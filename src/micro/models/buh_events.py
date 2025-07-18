from __future__ import annotations

from typing import Any, List, Optional, Union
from datetime import datetime

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.header_event import HeaderEvent

# fmt: off


class Document(HeaderEvent):
    """Создать бухгалтерский документ из базы"""
    ddk: datetime | None = Field(None, description="Дата документа YYYY.MM.DD", strict=True) # noqa
    nf: str = Field(..., description="Номер формы документа") # noqa
    ndok: str = Field(..., description="Номер документа") # noqa