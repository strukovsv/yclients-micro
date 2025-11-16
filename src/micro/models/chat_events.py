from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import Field

from micro.models.header_event import HeaderEvent


class InputChatEvent(HeaderEvent):
    """Входящее, перехваченное, сообщение от клиента"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    # fmt: on


class OutputChatEvent(HeaderEvent):
    """Ответное сообщение клиенту"""

    # fmt: off
    text: str = Field(..., description="Ответное сообщение", )  # noqa
    reply_text: str = Field(..., description="Исходное сообщение", )  # noqa
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    chat_id: str = Field(..., description="Идентификатор в телеграме",)  # noqa
    first_name: str | None = Field(None, description="Имя администратора в телеграме",)  # noqa
    last_name: str | None = Field(None, description="Фамилия администратора в телеграме",)  # noqa
    username: str | None = Field(None, description="Ник администратора в телеграме",)  # noqa
    # fmt: on


class AiChatEvent(HeaderEvent):
    """Ответное сообщение клиенту от Ai"""

    # fmt: off
    text: str = Field(..., description="Ответное сообщение", )  # noqa
    reply_text: str = Field(..., description="Исходное сообщение", )  # noqa
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    context: str = Field(..., description="Контекст сообщения",)  # noqa
    # fmt: on
