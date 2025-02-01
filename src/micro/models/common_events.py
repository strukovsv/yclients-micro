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


class ServiceStarted(HeaderEvent):
    """Сообщение о запуске сервиса"""

    service_name: str = Field(
        ..., description="Имя сервиса: sync, worker, bi, bot и т.д."
    )  # noqa


class InfoEvent(HeaderEvent):
    """Информационное сообщение
    bot: info.prolongation.service
    bot: info.test.message
    sync: info.sync.max.start
    sync: info.sync.max.end
    worker: info.report.card.insert
    worker: info.close.empty.service
    worker: info.close.empty.service.error
    worker: info.sms.chanels
    worker: info.report.card.update
    """

    text: Union[str, List[str]] = Field(
        ...,
        description="Текст информационного сообщения, строка или массив строк",
    )  # noqa


class ErrorEvent(HeaderEvent):
    """Отправлено сообщение об ошибке"""

    text: Union[str, List[str]] = Field(
        ..., description="Текст сообщения об ошибке, строка или массив строк"
    )  # noqa
