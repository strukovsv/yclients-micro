import logging

from aiokafka import AIOKafkaConsumer

from micro.singleton import MetaSingleton

import micro.config as config

from micro.schemes import Schema

logger = logging.getLogger(__name__)


class KafkaConsumer(metaclass=MetaSingleton):

    consumer: AIOKafkaConsumer = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            config.SRC_TOPIC,
            **config.CONSUMER_KAFKA,
            enable_auto_commit=config.KAFKA_ENABLE_AUTO_COMMIT,
            auto_offset_reset="earliest",
            retry_backoff_ms=10000,
        )
        logger.info(f"connect consumer kafka: {config.CONSUMER_KAFKA}")
        await self.consumer.start()

    async def get_messages(self):
        """Получить сообщения из kafka
        если соединения не установлено,
        то установить соединение и запустить kafka"""
        if not self.consumer:
            await self.start()
        return await self.consumer.getmany(
            timeout_ms=config.BATCH_TIMEOUT_SEC * 1000,
            max_records=config.BATCH_MAX_RECORDS,
        )

    async def partition_commit(self, tp, offset):
        """Пометить прочитанные записи обработанными"""
        if not config.KAFKA_ENABLE_AUTO_COMMIT:
            await self.consumer.commit({tp: offset})

    async def stop(self):
        """Остановить kafka соединение и отпустить объект"""
        if config.SRC_TOPIC and self.consumer:
            await self.consumer.stop()
            del self.consumer
            self.consumer = None


message_handlers: list = []
event_handlers: list = []


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


async def capture(message: dict) -> None:
    event_name = message.get("header", {}).get("event", None) or message.get(
        "event", None
    )
    # logger.info(f'capture: {message=} {message_handlers=}')
    # ++ legasy
    for handler in message_handlers:
        if handler["name"].lower() == event_name.lower():
            # logger.info(f"capture message: {message=}")
            await handler["handler"](message)
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
                # Вызвать функцию обработчик события, передать на вход объект
                await handler["handler"](data_obj)
            else:
                raise Exception(f"Не найдена model {event_name}")
