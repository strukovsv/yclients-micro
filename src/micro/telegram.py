import logging
import datetime

import httpx

import micro.config as config

logger = logging.getLogger(__name__)


async def get_request(url: str, params: dict):
    """Отправить get запрос"""
    # Клиент httpx
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                url,
                params=params,
                timeout=10.0,
            )
        except Exception as e:
            try:
                response = r.text
            except Exception:
                response = None
                logger.error(
                    f'httpx url: "{url}", response: "{response}", message: "{e}", params: "{params}"'  # noqa
                )


async def send_telegram(message: str, success: bool = None):
    """Отправить сообщение в телеграм

    :param str message: отправляемое сообщение
    :param bool success: отправить хороший или плохой смайлик
    """
    if config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT:
        for chat_id in (
            config.TELEGRAM_CHAT
            if isinstance(config.TELEGRAM_CHAT, list)
            else [config.TELEGRAM_CHAT]
        ):
            if chat_id:
                emoji = (
                    ("😀" if success else "☹")
                    if success is not None
                    else None
                )
                for message in [emoji, message]:
                    await get_request(
                        url=f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage",
                        params={
                            "chat_id": chat_id,
                            "text": message,
                            "parse_mode": "HTML",
                        },
                    )


async def send_start_service(service_name: str):
    date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await send_telegram(
        message="\U0001F680"
        + f"{date} : service <b>{service_name}</b> launched !"
    )
