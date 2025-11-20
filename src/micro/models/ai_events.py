from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic import Field

from micro.models.header_event import HeaderEvent


class AiRequest(HeaderEvent):
    """Входящее сообщение для AI"""

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    text: str = Field(..., description="Входящее сообщение", )  # noqa
    # fmt: on


class AiResponse(HeaderEvent):
    """Исходящее сообщение от AI"""

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента",)  # noqa
    text: str = Field(..., description="Исходящее сообщение", )  # noqa
    payload: dict = Field(..., description="Ответ как JSON", )  # noqa
    # fmt: on
