import logging
import json
import datetime

from aiokafka import AIOKafkaProducer

import config

logger = logging.getLogger(__name__)

producer = None


class KafkaProducer(AIOKafkaProducer):

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
            value=json.dumps(data, ensure_ascii=False).encode(),
        )


async def send_event(message: dict, event: str = None):
    global producer
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
        logger.info(f'send message "{message_id}" to "{event}"')
        await producer.send_kafka(id=js["message_id"], data=js)
