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

    async def send_kafka(self, id, data):
        """Отправить сообщение в kafka"""
        await self.send_and_wait(
            topic=config.DST_TOPIC,
            key=id.to_bytes(8, "big") if isinstance(id, int) else id.encode(),
            value=json.dumps(
                data, ensure_ascii=False, default=serialize_datetime
            ).encode(),
        )

    async def send_event(self, message: dict, event: str, obj: object = None):

        js = message.copy()
        # Создать идентификатор сообщения
        js["event_id"] = (
            config.PRODUCER_ID + "-" + datetime.datetime.now().isoformat()
        )
        # Сформировать route kye для сообщения
        if "message_key" not in js:
            js["message_key"] = js["event_id"]
        # deprecate историю сообщений
        # if js.get("event", None):
        #     js["events"] = js.get("events", []) + [js["event"]]
        js["event"] = event
        # Кратко распечатать 200 символов json
        js_example = {
            key: value
            for key, value in js.items()
            if key not in ("event", "event_id", "message_key")
        }
        sjs = f"{js_example}"[0:200]
        if obj:
            # Валидация объекта
            result = obj(**js)
            # logger.info(f'validate: {js=}')
            # logger.info(f'validate: {result.dict()=}')
            await self.send_kafka(id=js["message_key"], data=result.dict())
            logger.info(f'send validate message {js["event_id"]} to "{event}"')
        else:
            await self.send_kafka(id=js["message_key"], data=js)
            logger.info(f'send message {js["event_id"]} to "{event}"')


async def send_event(message: dict, event: str = None):
    await KafkaProducer().send_event(message, event)
