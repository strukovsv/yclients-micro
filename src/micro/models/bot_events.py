from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.base_event import BaseEvent

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
    access: List[str]
    password: str | None
    phone: str


class GetTextMessage(BaseEvent):
    """Введен текст в боте"""
    user: TelegramUser # noqa
    text: str # noqa
    message_id: int # noqa
    chat_id: int # noqa
    chat_id2: int # noqa
    pass


class GetReplyMessage(BaseEvent):
    """Введен ответ на текст в боте"""

    pass


class MenuItemSelected(BaseEvent):
    """Выбран пункт меню"""

    pass


class GetCommand(BaseEvent):
    """Введена команда"""

    pass
