from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.header_event import HeaderEvent

# fmt: off


class RecordUpdated(HeaderEvent):
    """Обновлена таблица records"""
    id: int = Field(..., description="Идентификатор записи records") # noqa
    data: YclientsRecord = Field(..., description="Новый объект record") # noqa
    old: YclientsRecord = Field(..., description="Старый объект record") # noqa


class RecordInserted(HeaderEvent):
    """Новая запись в таблице records"""
    id: int = Field(..., description="Идентификатор записи records") # noqa
    data: YclientsRecord = Field(..., description="Новый объект record") # noqa
