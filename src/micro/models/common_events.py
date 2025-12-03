from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.api_records import YclientsRecord
from micro.models.header_event import HeaderEvent


class Report(HeaderEvent):
    """Отправить сообщение

    Атрибут addresse будет содержать получателя сообщения
    client_id - отправить в yclient
    chat_id - отправить в telegram

    await Report(
        text=obj.text,
        plain=1,
        role="admin",
    ).send(
        client_id=obj.client_id
    )

    """

    # fmt: off
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on


class SaveMessageEvent(HeaderEvent):
    """Сохранить сообщение в истории"""

    # fmt: off
    client_id: int = Field(description="Идентификатор клиента")  # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on

    def route_key(self):
        return self.client_id


class ServiceStarted(HeaderEvent):
    """Сообщение о запуске сервиса"""

    service_name: str = Field(
        ..., description="Имя сервиса: sync, worker, bi, bot и т.д."
    )  # noqa
    date: str


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
    format: str | None = Field(
        None,
        description="Формат сообщения. Markdown (по умолчанию) или html",
    )  # noqa
    acc: str | None = Field(
        None,
        description="Отправить системное сообщение клиентам с заданным доступом",
    )  # noqa


class ErrorEvent(HeaderEvent):
    """Отправлено сообщение об ошибке"""

    text: Union[str, List[str]] = Field(
        ..., description="Текст сообщения об ошибке, строка или массив строк"
    )  # noqa


class Live(HeaderEvent):
    """Отправить сервисам запрос ответить жив он"""

    pass


class Webhook(HeaderEvent):
    """Входящие, перехваченное сообщение от клиента"""

    body: dict = Field(..., description="Перехваченное сообщение")  # noqa

    def route_key(self):
        return self.body.get("data", {}).get("id")
