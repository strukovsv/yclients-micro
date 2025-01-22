from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel


# fmt: off

class Header(BaseModel):
    event: str = Field(..., description="Имя сообщения") # noqa
    uuid: str = Field(..., description="Идентификатор сообщения") # noqa
    chain_uuid: str = Field(..., description="Идентификатор цепочки сообщений") # noqa
    desc: str | None = Field(None, description="Описание сообщения") # noqa
    version: str | None = Field(None, description="Версия сообщения") # noqa


class HeaderEvent(AvroBase):
    header: Header = Field(..., description="Заголовок сообщения") # noqa
