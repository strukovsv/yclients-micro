from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os

from micro.render_ext import to_text
from micro.models.common_events import Report, InfoEvent


# Настройка логгера
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 🧩 Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────


async def send_manager(template: str, **kwarg) -> None:
    """Отправить сообщение менеджерам."""
    message = await to_text(template=template, **kwarg)
    await InfoEvent(text=message).send()


async def send_client(template: str, debug: bool = False, **kwarg) -> None:
    """Отправить сообщение клиенту."""
    message = await to_text(template=template, **kwarg)
    client_id = kwarg.get("client_id")
    if client_id:
        if debug:
            await InfoEvent(
                text=f"""Отправлено клиенту {client_id}:

    {message}"""
            ).send()
        else:
            # Отправляем клиенту
            await Report(text=message, plain=1).send(
                client_id=client_id,
            )
    else:
        await InfoEvent(
            text=f"""Не отправлено клиенту!!:

{message}"""
        ).send()


def template_exists(template_name: str) -> bool:
    """Проверяет, существует ли файл шаблона в папке templates."""
    full_path = os.path.join("templates", template_name)
    return os.path.isfile(
        full_path
    )  # isfile — точнее, чем exists (не пропустит папки)


async def send_message(
    funnel_name: str, stage: str, debug: bool = False, **kwarg
) -> None:
    file_client = f"{funnel_name}/{stage}_client.txt".lower()
    if template_exists(file_client):
        await send_client(template=file_client, debug=debug, **kwarg)
        logger.info(f"send file client: {file_client}")

    file_manager = f"{funnel_name}/{stage}_manager.txt".lower()
    if template_exists(file_manager):
        await send_manager(template=file_manager, **kwarg)
        logger.info(f"send file manager: {file_manager}")
