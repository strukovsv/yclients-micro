from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Union

from pydantic import Field

from micro.models.header_event import HeaderEvent


class AiEvent(HeaderEvent):

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    # fmt: on

    def route_key(self):
        return self.client_id


class AiRequest(AiEvent):
    """Входящее сообщение для AI"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    # fmt: on


class AiResponse(AiEvent):
    """Исходящее сообщение от AI"""

    # fmt: off
    output: dict = Field(..., description="Исходящее объект", )  # noqa
    # fmt: on


class SignUpActivity(AiEvent):
    """Записаться на занятие"""

    # fmt: off
    activity_id: int = Field(..., description="Идентификатор занятия", )  # noqa
    # fmt: on


class UnsubscribeActivity(AiEvent):
    """Выписаться с занятия"""

    # fmt: off
    records_id: int = Field(..., description="Идентификатор записи", )  # noqa
    # fmt: on


class WillBeAbsent(AiEvent):
    """Клиент будет отсутствовать в это время"""

    # fmt: off
    absence_start: datetime | None = Field(
        default=None,
        description="Дата начала периода отсутствия клиента (например, отпуск)",
    )
    absence_end: datetime | None = Field(
        default=None, description="Дата окончания периода отсутствия клиента"
    )    # fmt: on


class AddClientToBlacklist(AiEvent):
    """Включить клиента в стоп лист"""

    # fmt: off
    blacklist_start: datetime | None = Field(
        default=None,
        description="Дата начала периода отсутствия клиента (например, отпуск)",
    )
    blacklist_stop: datetime | None = Field(
        default=None, description="Дата окончания периода отсутствия клиента"
    )    # fmt: on
