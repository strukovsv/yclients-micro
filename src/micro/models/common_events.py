from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.header_event import HeaderEvent


class Report(HeaderEvent):
    """Подготовлен отчет, реэультат операции
    Атрибут addresse будет содержать получателя сообщения
    """

    # fmt: off
    text: Union[str, List[str]] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    # fmt: on
