from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field


# fmt: off


class BaseEvent(AvroBase):
    event: str = Field(..., description="Имя сообщения") # noqa
    uid: str = Field(..., description="Идентификатор сообщения") # noqa
    chain_uid: str = Field(..., description="Идентификатор цепочки сообщений") # noqa
    desc: str | None = Field(None, description="Описание сообщения") # noqa
    version: str | None = Field(None, description="Версия сообщения") # noqa
