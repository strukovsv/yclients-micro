from __future__ import annotations

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field

from micro.models.header_event import HeaderEvent

# fmt: off


class SystemServiceStarted(HeaderEvent):
    """Сообщение о запуске сервиса"""
    service_name: str = Field(..., description="Имя сервиса: sync, worker, bi, bot и т.д.") # noqa


class SystemInfoMessage(HeaderEvent):
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
    text: Union[str, List[str]] = Field(..., description="Текст информационного сообщения, строка или массив строк") # noqa


class SystemErrorMessage(HeaderEvent):
    """Отправлено сообщение об ошибке"""
    text: Union[str, List[str]] = Field(..., description="Текст сообщения об ошибке, строка или массив строк") # noqa
