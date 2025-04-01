from __future__ import annotations

import logging
from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

import micro.pg_ext as base

from micro.models.header_event import HeaderEvent, PrintBaseEvent

logger = logging.getLogger(__name__)


class TimetableBaseClass(HeaderEvent):
    """Базовый класс для расписания"""


class FirstClientVisit(TimetableBaseClass):
    """Отправить сообщение клиенту о первой тренировке"""

    # fmt: off
    id: str = Field(..., description="Идентификатор клиента")  # noqa
    desc: str | None = Field(None, description="Расшифровка операции")  # noqa
    # fmt: on

    @classmethod
    def create(cls, id: str, desc: str):
        """Создать объект и заполнить из расписания"""
        return cls(id=id, desc=desc)


class TimetableProlong(TimetableBaseClass):
    """Пролонгировать тренировки на неделю
    шаблон тренировко в таблице week_schedule
    """

    # fmt: off
    date: str = Field(..., description="Дата начала пролонгации расписания, понедельник DD.MM.YYYY")  # noqa
    desc: str | None = Field(None, description="Расшифровка операции")  # noqa
    # fmt: on

    @classmethod
    def create(cls, id: str, desc: str):
        """Создать объект и заполнить из расписания"""
        return cls(date=id, desc=desc)


class TimetableAppendActive(TimetableBaseClass):
    """Создать тренировку тренировку"""

    # fmt: off
    time: str = Field(..., description="Время начала тренировки - 09:00:00")  # noqa
    service_title: str = Field(..., description="Наименование услуги - Здоровая спина")  # noqa
    service_id: int = Field(..., description="Идентификатор услуги - 15465147")  # noqa
    staff_name: str = Field(..., description="Сотрудник, имя - Кира")  # noqa
    staff_id: int = Field(..., description="Сотрудник, идентификатор - 3264159")  # noqa
    capacity: str = Field(..., description="Вместимость тренировки - 4")  # noqa
    resource_title: str = Field(..., description="Наименование зала - Большой зал")  # noqa
    resource_instance_ids: int = Field(..., description="Идентификатор зала (ресурса) - 170396")  # noqa
    length: int = Field(..., description="Продолжительность занятия, в сек - 3600")  # noqa
    date: str = Field(..., description="Дата и время начала занятия - 2025-02-10 09:00:00")  # noqa
    # fmt: on


class TimetableDeleteActive(TimetableBaseClass):
    """Удалить групповое событие"""

    # fmt: off
    activity_id: int = Field(..., description="Идентификатор группового события")  # noqa
    desc: str = Field(..., description="Расшифровка группового события")  # noqa
    # fmt: on

    @classmethod
    def create(cls, id: str, desc: str):
        """Создать объект и заполнить"""
        return cls(activity_id=int(id), desc=desc)

    def route_key(self):
        return self.activity_id


class TimetablePrint(PrintBaseEvent):
    """Распечатать расписание для сотрудника и для админа"""
