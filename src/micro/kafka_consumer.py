import logging
import json
import datetime
import traceback
import asyncio

from aiokafka import AIOKafkaConsumer

from micro.singleton import MetaSingleton

import micro.config as config

from micro.schemes import Schema
from micro.logging_trace import TRACE

from micro.kafka_producer import KafkaProducer

from .metrics import DO_EVENTS_CNT, WORKED_EVENTS_CNT, EVENTS_SENT_DLQ_CNT

logger = logging.getLogger(__name__)


class KafkaConsumer(metaclass=MetaSingleton):

    consumer: AIOKafkaConsumer = None

    async def start(self):
        logger.info(f"connect consumer kafka: {config.CONSUMER_KAFKA}")
        self.consumer = AIOKafkaConsumer(
            **config.CONSUMER_KAFKA,
            # Отключает автоматическую отправку подтверждений (commit)
            # о прочитанных смещениях (offset).
            # Вы сами отвечаете за вызов consumer.commit()
            # после успешной обработки сообщения.
            enable_auto_commit=False,
            # Определяет, с какого места начинать чтение,
            # когда у группы потребителей нет сохранённого смещения (первый запуск)
            # или сохранённое смещение удалено/невалидно.
            # "latest" – читать только новые сообщения,
            # которые будут приходить после запуска.
            auto_offset_reset="latest",
        )
        topics = []
        if config.SRC_TOPIC:
            topics.append(config.SRC_TOPIC)
        if config.LOCAL_TOPIC:
            topics.append(config.LOCAL_TOPIC)
        if config.DLQ_READ_TOPIC:
            topics.append(config.DLQ_READ_TOPIC)
        if topics:
            self.consumer.subscribe(topics=topics)
            logger.info(f"subscribe topics: {topics}")
        else:
            if config.SRC_PATTERN_TOPIC:
                self.consumer.subscribe(pattern=config.SRC_PATTERN_TOPIC)
                logger.info(
                    f"subscribe topic pattern: {config.SRC_PATTERN_TOPIC}"
                )
            else:
                raise Exception("Service not source topics")
        await self.consumer.start()

    async def get_messages(self):
        """Получить сообщения из kafka
        если соединения не установлено,
        то установить соединение и запустить kafka"""
        if not self.consumer:
            await self.start()
        try:
            data = await asyncio.wait_for(
                self.consumer.getmany(
                    timeout_ms=config.BATCH_TIMEOUT_SEC * 1000,
                    max_records=config.BATCH_MAX_RECORDS,
                ),
                timeout=config.KAFKA_READ_TIMEOUT_SEC,
            )
            return data
        except asyncio.TimeoutError:
            logger.error("Kafka poll timeout")
            return {}
        except Exception as e:
            logger.error(f"Kafka poll failed {e}")
            return {}

    async def partition_commit(self, tp, offset):
        """Пометить прочитанные записи обработанными"""
        await self.consumer.commit({tp: offset})

    async def stop(self):
        """Остановить kafka соединение и отпустить объект"""
        if (config.SRC_TOPIC or config.SRC_PATTERN_TOPIC) and self.consumer:
            await self.consumer.stop()
            del self.consumer
            self.consumer = None


message_handlers: list = []
event_handlers: list = []
all_event_handlers: list = []


def message_handler(event_name):

    def decorator(handler):
        message_handlers.append({"name": event_name, "handler": handler})
        return handler

    return decorator


def event_handler(event_name):

    def decorator(handler):
        event_handlers.append({"name": event_name, "handler": handler})
        return handler

    return decorator


def all_event_handler():

    def decorator(handler):
        all_event_handlers.append({"handler": handler})
        return handler

    return decorator


async def capture_dict(message: dict) -> None:
    # Получить имя события
    header: dict = message.get("header", {})
    event_name = header.get("event", None) or message.get("event", None)

    def logger_capture_event():
        if header:
            source = header.get("source")
            uuid = header.get("uuid")
            trace_id = header.get("trace_id")
            if trace_id:
                TRACE().set(trace_id)
            else:
                TRACE().new()
            logger.info(
                f'get event from "{source}" '
                + f'-> "{event_name}" with uuid={uuid}'
            )

    # ++ legasy
    for handler in message_handlers:
        if handler["name"].lower() == event_name.lower():
            logger_capture_event()
            await handler["handler"](message)
            # Обработано входящее событие
            WORKED_EVENTS_CNT.inc()
    # -- legasy
    # Перебрать все обработчики событий
    for handler in event_handlers:
        # Найти свой обработчик
        if handler["name"].lower() == event_name.lower():
            # logger.info(f"capture event: {message=}")
            # Найти свою модель
            obj = Schema().get_models().get(event_name, None)
            if obj:
                # Получить объект из json
                data_obj = obj(**message)
                # Вызвать метод дополнителной сереализации
                await data_obj.deserialization()
                # Вывести пришло событие
                logger_capture_event()
                # Вызвать функцию обработчик события, передать на вход объект
                await handler["handler"](data_obj)
                # Обработано входящее событие
                WORKED_EVENTS_CNT.inc()
            else:
                raise Exception(f"Не найдена model {event_name}")


async def capture(message: object, events=None) -> None:
    # Входящее событие в сервис
    DO_EVENTS_CNT.inc()
    # Перехватить все входящие сообщения
    for handler in all_event_handlers:
        # Вызвать функцию обработчик события, передать на вход объект
        await handler["handler"](message)
        WORKED_EVENTS_CNT.inc()
    if message_handlers or event_handlers:
        # Добавить в сообщение время создания
        message_dict = json.loads(message.value)
        message_dict["create_event_timestamp"] = (
            datetime.datetime.fromtimestamp(message.timestamp / 1000).strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        )
        # Обработать сообщение
        if config.DLQ_WRITE_TOPIC:
            try:
                # legasy
                if events:
                    await events.do(message_dict)
                # new
                await capture_dict(message_dict)
            except Exception as e:
                err = traceback.format_exc()
                # Добавить в текущее сообщение данные об ошибке
                message_dict["attempt"] = message_dict.get("attempt", 0) + 1
                message_dict["error_message"] = str(e)
                message_dict["traceback"] = err.split("\n")
                now_isoformat = datetime.datetime.now().isoformat()
                message_dict["error_at"] = now_isoformat
                message_dict["first_error_at"] = message_dict.get(
                    "first_error_at", now_isoformat
                )
                # Отправить сообщение в топик ошибок сервиса
                await KafkaProducer().send_kafka_topic(
                    topic=config.DLQ_WRITE_TOPIC, key=None, data=message_dict
                )
                # Метрика !!!
                EVENTS_SENT_DLQ_CNT.inc()
                logger.error(err)
                logger.info(
                    f"sended error message to topic {config.DLQ_WRITE_TOPIC}"
                )
        else:
            # legasy
            if events:
                await events.do(message_dict)
            # new
            await capture_dict(message_dict)
