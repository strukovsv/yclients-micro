from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord

# fmt: off


class BaseEvent(AvroBase):
    event: str = Field(..., description="Имя сообщения") # noqa
    event_id: str = Field(..., description="Идентификатор сообщения") # noqa
    message_key: str = Field(..., description="Идентификатор цепочки сообщений") # noqa
    desc: str | None = Field(None, description="Описание сообщения") # noqa
    version: str | None = Field(None, description="Версия сообщения") # noqa
