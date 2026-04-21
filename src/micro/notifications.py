import logging

import micro.config as config

from micro.max import send_max

logger = logging.getLogger(__name__)


async def send_notification(channel: str, message: str):
    if channel.lower() == "dlq":
        await send_max(
            chat_id=config.get_env("DLQ_MAX_GROUP_ID"), message=message
        )
    else:
        raise Exception(f'Не задан канал нотификаций "{channel}"')
