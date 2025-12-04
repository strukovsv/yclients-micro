from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import Field

from micro.models.header_event import HeaderEvent


class BaseChatEvent(HeaderEvent):
    client_id: int = Field(
        ...,
        description="Идентификатор клиента",
    )  # noqa

    def route_key(self):
        return self.client_id


class InputChatEvent(BaseChatEvent):
    """Входящее, перехваченное, сообщение от клиента"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    # fmt: on


class InputCommandEvent(BaseChatEvent):
    """Входящее, перехваченное, сообщение от клиента, команда"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    # fmt: on


class ClientChatEvent(BaseChatEvent):
    """Входящее, перехваченное, сообщение от клиента"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    # fmt: on


class YclientChatEvent(BaseChatEvent):
    """Входящее, перехваченное, сообщение от клиента"""

    # fmt: off
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    # fmt: on


class OutputChatEvent(BaseChatEvent):
    """Ответное сообщение клиенту"""

    # fmt: off
    text: str = Field(..., description="Ответное сообщение", )  # noqa
    reply_text: str = Field(..., description="Исходное сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    chat_id: str = Field(..., description="Идентификатор в телеграме",)  # noqa
    first_name: str | None = Field(None, description="Имя администратора в телеграме",)  # noqa
    last_name: str | None = Field(None, description="Фамилия администратора в телеграме",)  # noqa
    username: str | None = Field(None, description="Ник администратора в телеграме",)  # noqa
    # fmt: on


class AiChatEvent(BaseChatEvent):
    """Ответное сообщение клиенту от Ai"""

    # fmt: off
    text: str = Field(..., description="Ответное сообщение", )  # noqa
    reply_text: str = Field(..., description="Исходное сообщение", )  # noqa
    phone: str = Field(..., description="Телефон",)  # noqa
    display_name: str = Field(..., description="Наименование клиента",)  # noqa
    context: str = Field(..., description="Контекст сообщения",)  # noqa
    # fmt: on
