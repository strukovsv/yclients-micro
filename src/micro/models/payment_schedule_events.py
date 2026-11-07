"""Сигнал запуска домена payment в worker; данные графика не передаются."""

from pydantic import Field
from micro.models.header_event import HeaderEvent


class PaymentScheduleRun(HeaderEvent):
    notify: bool = Field(
        False, description="Подготовить нотификации через InfoEvent(acc=pay)"
    )

    @classmethod
    def create(cls, data: dict):
        """Совместимость с jobs: служебные args не становятся полями контракта.

        :param dict data: аргументы crontab
        """
        return cls(notify=data.get("notify", False))
