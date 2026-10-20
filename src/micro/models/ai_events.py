from __future__ import annotations

from datetime import datetime

from pydantic import Field

from micro.models.header_event import HeaderEvent


class AiClientEvent(HeaderEvent):

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    # fmt: on

    def route_key(self):
        return self.client_id


class AiClientRequest(AiClientEvent):
    """Входящее сообщение для AiClient от клиента"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    # fmt: on


class AiClientResponse(AiClientEvent):
    """Исходящее сообщение от AiClient клиенту"""

    # fmt: off
    output: dict = Field(..., description="Исходящее объект", )  # noqa
    # fmt: on


class AiClientHelp(AiClientEvent):
    """AiClient проист помощи у администратора"""

    # fmt: off
    output: dict = Field(..., description="Исходящее объект", )  # noqa
    # fmt: on


class SignUpActivity(AiClientEvent):
    """Записаться на занятие"""

    # fmt: off
    activity_id: int = Field(..., description="Идентификатор занятия", )  # noqa
    # fmt: on


class UnsubscribeActivity(AiClientEvent):
    """Выписаться с занятия"""

    # fmt: off
    records_id: int = Field(..., description="Идентификатор записи", )  # noqa
    # fmt: on


class WillBeAbsent(AiClientEvent):
    """Клиент будет отсутствовать в это время"""

    # fmt: off
    absence_start: datetime | None = Field(
        default=None,
        description="Дата начала периода отсутствия клиента (например, отпуск)", # noqa
    )
    absence_end: datetime | None = Field(
        default=None, description="Дата окончания периода отсутствия клиента"
    )
    # fmt: on


class AddClientToBlacklist(AiClientEvent):
    """Включить клиента в стоп лист"""

    # fmt: off
    blacklist_start: datetime | None = Field(
        default=None,
        description="Дата начала периода отсутствия клиента (например, отпуск)", # noqa
    )
    blacklist_stop: datetime | None = Field(
        default=None, description="Дата окончания периода отсутствия клиента"
    )
    # fmt: on


class AiStaffEvent(HeaderEvent):

    # fmt: off
    staff_id: int = Field(..., description="Идентификатор сотрудника",)  # noqa
    # fmt: on

    def route_key(self):
        return self.staff_id


class AiStaffRequest(AiStaffEvent):
    """Входящее сообщение для Ai от сотрудника"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    # fmt: on


class AiStaffResponse(AiStaffEvent):
    """Исходящее сообщение от Ai сотруднику"""

    # fmt: off
    output: str = Field(..., description="Исходящее объект", )  # noqa
    # fmt: on
