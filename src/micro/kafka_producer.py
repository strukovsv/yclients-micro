import logging
import json
import datetime

from aiokafka import AIOKafkaProducer

from micro.singleton import MetaSingleton

import micro.config as config

logger = logging.getLogger(__name__)


def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()


class KafkaProducer(AIOKafkaProducer, metaclass=MetaSingleton):

    def __init__(self):
        if config.PRODUCER_KAFKA["bootstrap_servers"]:
            super().__init__(
                **config.PRODUCER_KAFKA,
                enable_idempotence=config.ENABLE_IDEMPOTENCE,
            )
            logger.info(f"connect producer kafka: {config.PRODUCER_KAFKA}")

    async def send_kafka(self, key: any, data: dict) -> None:
        """Отправить сообщение

        :param any key: route key
        :param dict data: сообщение
        """
        await self.send_and_wait(
            topic=config.DST_TOPIC,
            key=str(key).encode(),
            value=json.dumps(
                data, ensure_ascii=False, default=serialize_datetime
            ).encode(),
        )

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
            config.PRODUCER_ID + "-" + datetime.datetime.now().isoformat()
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
