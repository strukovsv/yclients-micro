from __future__ import annotations

from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.base_event import BaseEvent

# fmt: off


class RecordUpdated(BaseEvent):
    """Обновлена таблица records"""
    id: int = Field(..., description="Идентификатор записи records") # noqa
    data: YclientsRecord = Field(..., description="Новый объект record") # noqa
    old: YclientsRecord = Field(..., description="Старый объект record") # noqa


class RecordInserted(BaseEvent):
    """Новая запись в таблице records"""
    id: int = Field(..., description="Идентификатор записи records") # noqa
    data: YclientsRecord = Field(..., description="Новый объект record") # noqa
