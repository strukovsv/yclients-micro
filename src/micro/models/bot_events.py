from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.header_event import HeaderEvent

# fmt: off


class TelegramUser(AvroBase):
    id: int
    name: str
    first_name: str
    last_name: str
    telegram_id: str
    telegram_username: str
    client_id: int | None
    staff_id: int | None
    access: List[str] | None
    password: str | None
    phone: str | None


class BotEnteredTextMessage(HeaderEvent):
    """Введен текст в боте"""
    user: TelegramUser # noqa
    text: str # noqa
    message_id: int # noqa
    chat_id: int # noqa


class BotEnteredReplyMessage(HeaderEvent):
    """Введен ответ на текст в боте"""

    pass


class BotMenuItemSelected(HeaderEvent):
    """Выбран пункт меню"""

    pass


class BotEnteredCommand(HeaderEvent):
    """Введена команда"""

    pass
