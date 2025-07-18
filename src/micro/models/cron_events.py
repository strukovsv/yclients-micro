from __future__ import annotations

import logging
from typing import Any, List, Dict, Optional

from pydantic import Field

from micro.models.header_event import HeaderEvent, PrintBaseEvent

logger = logging.getLogger(__name__)


class CronBaseClass(HeaderEvent):
    """Базовый класс для cron событий"""


class ScheduleReport(CronBaseClass):
    """Отправить сообщение (сформировать отчет) клиенту или администратору"""

    # fmt: off
    data: List[Dict[str, Any]] = Field(description="Строки отчета")  # noqa
    # fmt: on

    @classmethod
    def create(cls, data: List[Dict[str, Any]]):
        """Создать объект и заполнить из расписания"""
        return cls(data=data)
