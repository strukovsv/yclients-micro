from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

from micro.models.header_event import HeaderEvent

# fmt: off


class TelegramUser(BaseModel):
    """Пользователь в telegram"""
    id: int # noqa
    name: str # noqa
    first_name: str # noqa
    last_name: str # noqa
    telegram_id: str # noqa
    telegram_username: str # noqa
    client_id: int | None # noqa
    staff_id: int | None # noqa
    access: List[str] | None # noqa
    password: str | None # noqa
    phone: str | None # noqa


class BotEnteredTextMessage(HeaderEvent):
    """Введен текст в боте"""
    user: TelegramUser # noqa
    text: str # noqa
    message_id: int # noqa
    chat_id: int # noqa


class BotEnteredReplyMessage(HeaderEvent):
    """Введен ответ на текст в боте"""
    user: TelegramUser # noqa
    text: str # noqa
    message_id: int # noqa
    chat_id: int # noqa
    reply_text: str # noqa
    reply_message_id: int # noqa


class BotMenuItemSelected(HeaderEvent):
    """Выбран пункт меню"""

    pass


class BotEnteredCommand(HeaderEvent):
    """Введена команда"""

    pass
