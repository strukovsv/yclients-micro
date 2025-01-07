import logging

from aiokafka import AIOKafkaConsumer

from micro.singleton import MetaSingleton

import micro.config as config

logger = logging.getLogger(__name__)


class KafkaConsumer(AIOKafkaConsumer, metaclass=MetaSingleton):

    def __init__(self):
        if config.CONSUMER_KAFKA["bootstrap_servers"]:
            super().__init__(
                config.SRC_TOPIC,
                **config.CONSUMER_KAFKA,
                enable_auto_commit=config.KAFKA_ENABLE_AUTO_COMMIT,
                auto_offset_reset="earliest",
            )
            logger.info(f"connect consumer kafka: {config.CONSUMER_KAFKA}")

    async def get_messages(self):
        return await self.getmany(
            timeout_ms=config.BATCH_TIMEOUT_SEC * 1000,
            max_records=config.BATCH_MAX_RECORDS,
        )

    async def partition_commit(self, tp, offset):
        if not config.KAFKA_ENABLE_AUTO_COMMIT:
            await self.commit({tp: offset})
