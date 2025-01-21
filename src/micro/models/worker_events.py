from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.header_event import HeaderEvent

# fmt: off


class ReportReady(HeaderEvent):
    """Подготовлен отчет для клиента"""
    text: Union[str, List[str]] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    client_id: int | None = Field(None, description="Идентификатор клиента в yclients") # noqa
    telegram_id: int | None = Field(None, description="Идентификатор клиента в telegram") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa