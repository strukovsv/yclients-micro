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

    async def send_event(self, message: dict, event: str = None):
        js = message.copy()
        if "message_id" not in js:
            js["message_id"] = (
                config.PRODUCER_ID + "-" + datetime.datetime.now().isoformat()
            )
        event = event if event else js.get("answer", None)
        if event:
            if js.get("event", None):
                js["events"] = js.get("events", []) + [js["event"]]
            js["event"] = event
            message_id = js["message_id"]
            #        logger.info(f'send message "{message_id}" to "{event}", data: {js}')
            # Кратко распечатать 200 символов json
            js_example = {
                key: value
                for key, value in js.items()
                if key not in ("event", "message_id")
            }
            sjs = f"{js_example}"[0:200]
            logger.info(f'send message "{message_id}" to "{event}" : "{sjs}"')
            await self.send_kafka(id=js["message_id"], data=js)


async def send_event(message: dict, event: str = None):
    await KafkaProducer().send_event(message, event)