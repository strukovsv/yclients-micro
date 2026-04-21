import logging

import httpx

import micro.config as config

logger = logging.getLogger(__name__)


async def send_max(chat_id: int, message: str):
    """Отправить сообщение в телеграм

    :param str message: отправляемое сообщение
    :param bool success: отправить хороший или плохой смайлик
    """
    if config.MAX_TOKEN and chat_id:

        url = f"https://platform-api.max.ru/messages?chat_id={chat_id}"
        payload = {"text": message}
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": config.MAX_TOKEN,
        }

        logger.info(f"{url=}")

        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=10.0,
                )
                logger.info(f"{r.text=}")
            except Exception as e:
                try:
                    response = r.text
                except Exception:
                    response = None
                    logger.error(
                        f'httpx url: "{url}", response: "{response}", message: "{e}"'  # noqa
                    )
    else:
        raise Exception("Не задан канал max токен или чат отправки")
