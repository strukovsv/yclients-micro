from __future__ import annotations

from enum import StrEnum

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
    channel - отправить в топик канала

    await Report(
        text=obj.text,
        plain=1,
        role="admin",
    ).send(
        client_id=obj.client_id
    )

    """

    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on


class MessagePreparedForStaff(HeaderEvent):
    """Сообщение для персонала готово к отправке в telegram бот"""
    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
    chat_id: int = Field(..., description="Идентификатор чата администратора") # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on


class MessagePreparedForClient(HeaderEvent):
    """Сообщение для клиента готово к отправке через внешнее API"""
    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
    client_id: int = Field(..., description="Идентификатор клиента в yclients") # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on


class MessageSentToClient(HeaderEvent):
    """Сообщение успешно отправлено клиенту и мы получили код сообщения"""
    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
    client_id: int = Field(..., description="Идентификатор клиента в yclients") # noqa
    phone: str = Field(..., description="Телефон клиента") # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    notification_id: str = Field(None, description="Идентификатор отправленного сообщения") # noqa
    # fmt: on


class MessagePreparedForChat(HeaderEvent):
    """Сообщение подготовлено для отправки в топик чата
    Попытка реализовать чат с клиентом на каналах и топиках
    Не взлетело :(
    """
    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
    channel: str = Field(..., description="Идентификатор канала") # noqa
    text: Union[str, List[str | None], None] = Field(..., description="Текст отчета, строка или массив строк") # noqa
    type: str | None = Field(None, description="Тип отчета: html, markdown") # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    role: str | None = Field(None, description="Роль по умолчанию, если не задана, то отправил сервис") # noqa
    # fmt: on


class MessageStatusReceived(HeaderEvent):
    """Пришел от fromni статус отправленного сообщения"""

    # fmt: off
    fromni_client_id: str = Field(..., description="Идентификатор клиента в fromni") # noqa
    phone: str = Field(..., description="Телефон клиента") # noqa
    status: str = Field(..., description="Статус отправленного сообщения") # noqa
    cannel: str = Field(..., description="Канал") # noqa
    # fmt: on


class MessageReceivedFromClient(HeaderEvent):
    """Пришло новое сообщение от клиента"""

    # fmt: off
    text: str = Field(..., description="Текст сообщения") # noqa
    phone: str = Field(..., description="Телефон клиента") # noqa
    # fmt: on


class SaveMessageEvent(HeaderEvent):
    """Сохранить сообщение в истории"""

    # fmt: off
    sender: str | None = Field(None, description="Кто отправил сообщение клиенту") # noqa
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

    body: dict = Field(..., description="Перехваченное сообщение")  # noqa


class WebhookFromniReceived(Webhook):
    """Входящие, перехваченное сообщение от клиента Fromni"""

    def route_key(self):
        key = self.body.get("data", {}).get("contact", {}).get("phone")
        if not key:
            for data in self.body.get("data", {}).get("docs", []):
                key = data.get("data", {}).get("phone")
        return f'{self.body.get("type")}::{key}'


class WebhookCrmReceived(Webhook):

    pass
    # def route_key(self):
    #     return None


class WebhookYclientsReceived(Webhook):

    pass
    # def route_key(self):
    #     return None


class ReportRequestedType(StrEnum):

    TRADING_REPORT = "Trading report"
    TRADING_REPORT_BRIEF = "Trading report brief"


class ReportRequested(HeaderEvent):
    """Запрошен пользователем отчет"""

    # fmt: off
    report_type: ReportRequestedType = Field(..., description="Тип отчета")
    period: str = Field(..., description="Период отчета")
    # fmt: on
