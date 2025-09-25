import logging
import json
from datetime import datetime, date, time, timedelta
from typing import Any

from aiokafka import AIOKafkaProducer

from micro.singleton import MetaSingleton

# from micro.models.header_event import HeaderEvent, Header

import micro.config as config

logger = logging.getLogger(__name__)


def serialize_datetime(obj: Any) -> str | float:
    """
    Сериализует объекты datetime, date, time, timedelta в строки или числа.

    Поддерживаемые типы:
        - datetime.datetime → ISO формат с временем: "2025-08-11T14:30:00"
        - datetime.date      → ISO формат даты: "2025-08-11"
        - datetime.time      → ISO формат времени: "14:30:00"
        - datetime.timedelta → float (секунды) ИЛИ строка в формате ISO 8601 (по желанию)

    Для использования с json.dumps:
        json.dumps(data, default=serialize_datetime)

    :param obj: Любой объект для сериализации
    :return: Сериализованное значение (str или float)
    :raises TypeError: Если тип не поддерживается
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, time):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        # Вариант 1: возвращаем общее количество секунд (float)
        return obj.total_seconds()

        # --- Альтернатива: возвращать в формате ISO 8601 (например, "PT2H30M") ---
        # from isodate import duration_isoformat  # требует pip install isodate
        # return duration_isoformat(obj)
        #
        # Но без внешних зависимостей можно сделать вручную:
        # days = obj.days
        # seconds = obj.seconds
        # hours, remainder = divmod(seconds, 3600)
        # minutes, seconds = divmod(remainder, 60)
        # parts = ["P"]
        # if days: parts.append(f"{days}D")
        # if hours or minutes or seconds:
        #     parts.append("T")
        #     if hours: parts.append(f"{hours}H")
        #     if minutes: parts.append(f"{minutes}M")
        #     if seconds: parts.append(f"{seconds}S")
        # return "".join(parts) if len(parts) > 1 else "PT0S"

    # Раскомментируйте, если нужно пропускать None
    # elif obj is None:
    #     return None

    raise TypeError(
        f"Объект типа {type(obj).__name__} не поддерживается для сериализации"
    )


class KafkaProducer(metaclass=MetaSingleton):

    producer: AIOKafkaProducer = None

    async def start(self):
        if config.DST_TOPIC:
            self.producer = AIOKafkaProducer(
                **config.PRODUCER_KAFKA,
                enable_idempotence=config.ENABLE_IDEMPOTENCE,
                retry_backoff_ms=10000,
            )
            logger.info(f"connect producer kafka: {config.PRODUCER_KAFKA}")
            await self.producer.start()

    async def send_kafka(self, key: any, data: dict) -> None:
        """Отправить сообщение

        :param any key: route key
        :param dict data: сообщение
        """
        if not self.producer:
            await self.start()
        await self.producer.send_and_wait(
            topic=config.DST_TOPIC,
            key=str(key).encode(),
            value=json.dumps(
                data, ensure_ascii=False, default=serialize_datetime
            ).encode(),
        )

    async def stop(self):
        """Остановить kafka соединение и отпустить объект"""
        if config.DST_TOPIC and self.producer:
            await self.producer.stop()
            del self.producer
            self.producer = None

    async def send_event(
        self, event: str, message: dict, key: any = None, obj: object = None
    ) -> None:
        """Отправить сообщение в topic

        :param str event: тип сообщения
        :param dict message: отправляемое сообщение
        :param any key: route key для topic, defaults to None
        :param object obj: объект валидации сообщения, defaults to None
        """
        # Скопировать текущее сообщение и обоготить его
        js = message.copy()
        # Тип сообщения
        js["event"] = event
        # Создать идентификатор сообщения
        js["uuid"] = (
            config.PRODUCER_ID + "-" + datetime.now().isoformat()
        )
        # Сформировать атрибут для цепочки сообщений
        if "chain_uuid" not in js:
            js["chain_uuid"] = js["uuid"]
        # Валидация объекта
        if obj:
            try:
                # Создать объект по dict
                result = obj(**js)
                # Обратно получить dict из объекта
                js = result.dict()
            except Exception as e:
                logger.error(
                    f'Ошибка "{e}" валидации сообщения "{js}" по типу "{obj}"'
                )
        # Отправить сообщение
        await self.send_kafka(key=key if key else "na", data=js)
        logger.info(f'send event "{event}"')


# async def send_event(message: dict, event: str = None):
#     await KafkaProducer().send_event(event=event, key="na", message=message)
