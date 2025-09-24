"""
Модуль событий, связанных с планировщиком (cron) и workflow-воронками.

Содержит базовые и конкретные классы событий для:
- Отправки отчетов по расписанию
- Управления многоэтапными workflow (например, воронка реактивации клиентов)

Все события наследуются от HeaderEvent и используют единый интерфейс для
хранения данных и управления состоянием.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os
import json

from micro.render_ext import to_text
from micro.models.common_events import Report, InfoEvent

from pydantic import Field

from micro.models.header_event import HeaderEvent
from micro.pg_ext import fetchone, execute

from micro.utils import str_to_timedelta
from micro.send_messages import send_message

# Настройка логгера
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 🧱 Базовые классы
# ─────────────────────────────────────────────────────────────────────────────


class CronBaseClass(HeaderEvent):
    """
    Базовый класс для всех событий, запускаемых по расписанию (cron).

    Предоставляет структуру для хранения списка данных, которые будут обработаны.
    """

    data: Dict[str, Any]

    @classmethod
    def create(cls, data: List[Dict[str, Any]]) -> "CronBaseClass":
        """
        Создает экземпляр события на основе переданных данных.

        :param data: Список словарей с данными для события
        :return: Экземпляр класса события
        """
        return cls(data=data)


class WorkflowBase(CronBaseClass):
    """
    Базовый класс для событий, управляющих многоэтапными workflow (воронками).

    Предоставляет методы для получения и смены текущего этапа workflow,
    а также для отложенного перехода между этапами.

    Ожидаемая структура данных:
        obj.data = [
            {
                "event": "StartWorkflow",
                "id": "272696997::20250811",
                "workflow": "ReactivationClient",
                "workflow_id": 304734851,
                "client_id": 272696997,
                "client_name": "+79135602444 Дарья",
                "last_training_date": datetime.date(2025, 8, 11),
                "current_record_date": None,
                "cards": None,
            }
        ]
    """

    def get_workflow(self) -> Optional[str]:
        return self.__class__.__name__

    def get_stage(self) -> Optional[str]:
        """
        Получает текущий активный этап workflow из базы данных.
        :return: Название текущего этапа или None, если этап не найден или данные некорректны.
        """
        return self.data.get("stage")

    def get_data(self) -> dict:
        """
        Получает текущий активный этап workflow из базы данных.
        :return: Название текущего этапа или None, если этап не найден или данные некорректны.
        """
        return self.data.get("js", self.data)

    async def to_stage(
        self,
        workflow_id: str,
        from_stage: str,
        stage: Optional[str] = None,
        delay: Optional[str | timedelta] = None,
    ) -> None:
        """
        Переводит workflow на указанный этап. Если этап не указан — завершает текущий этап.

        При указании `delay` — новый этап будет запланирован на указанное время в будущем.

        :param stage: Название нового этапа. Если None — просто закрывает текущий этап.
        :param delay: Задержка перед стартом нового этапа.
                           Может быть строкой (например, "30s", "1d") или объектом timedelta.
        :raises ValueError: Если delay имеет неподдерживаемый тип.
        """

        # Преобразование строки в timedelta, если необходимо
        delay_timedelta: Optional[timedelta] = None
        if delay is not None:
            if isinstance(delay, str):
                delay_timedelta = str_to_timedelta(delay)
            elif isinstance(delay, timedelta):
                delay_timedelta = delay
            else:
                raise ValueError(
                    "Параметр 'delay' должен быть строкой или объектом timedelta"
                )

        logger.info(f"Смена этапа: {stage=}, {delay=}, {delay_timedelta=}")

        current_timestamp = datetime.now()

        # SQL-операции: завершить текущий этап + создать новый (если указан)
        sql_operations = [
            {
                "sql": """
                    UPDATE workflow_stages
                    SET executed_at = %(current_timestamp)s
                    WHERE workflow = %(workflow)s
                      AND workflow_id = %(workflow_id)s
                      AND executed_at IS NULL
                """,
                "params": {
                    # Получить имя воронки, процесса
                    "workflow": self.get_workflow(),
                    # Идентификатор, уникальность воронки
                    "workflow_id": str(workflow_id),
                    # Простамить текущее время
                    "current_timestamp": current_timestamp,
                },
            }
        ]

        # Если stage не задан, то считаем, что тольок завершить текущий stage
        if stage is not None:
            data = self.get_data()
            # Удалить состояние что-бы не смущала
            data.pop("stage", None)
            started_at = (
                current_timestamp + delay_timedelta
                if delay_timedelta
                else current_timestamp
            )
            sql_operations.append(
                {
                    "sql": """
                        INSERT INTO workflow_stages (
                            workflow,
                            workflow_id,
                            from_stage,
                            stage,
                            created_at,
                            started_at,
                            js
                        ) VALUES (
                            %(workflow)s,
                            %(workflow_id)s,
                            %(from_stage)s,
                            %(stage)s,
                            %(current_timestamp)s,
                            %(started_at)s,
                            %(js)s
                        )
                    """,
                    "params": {
                        "workflow": self.get_workflow(),
                        "workflow_id": str(workflow_id),
                        "stage": stage,
                        "current_timestamp": current_timestamp,
                        "started_at": started_at,
                        "js": json.dumps(data, ensure_ascii=True),
                        "from_stage": from_stage,
                    },
                }
            )

        # Выполняем все операции в одной транзакции
        await execute(query=sql_operations)
        logger.info(f"Этап workflow успешно обновлен: {stage or 'закрыт'}")

    async def stage_worker(
        self,
        funnel_name: str,
        stages: dict,
        workflow_id: str,
        debug: bool = False,
        **kwarg,
    ):
        # Получить текущее состояние
        stage_name = self.get_stage()
        # Получить текущую задачу
        stage = stages.get(stage_name)
        if stage:
            logger.info(f"{stage=}")
            # Отправить сообщение клиенту и администратору
            await send_message(
                funnel_name=funnel_name,
                stage=stage_name,
                debug=debug,
                workflow=self.get_workflow(),
                workflow_id=workflow_id,
                **kwarg,
            )
            # Если задан, то запустить следующий этап с задержкой
            if stage.get("next"):
                await self.to_stage(
                    from_stage=stage_name,
                    workflow_id=workflow_id,
                    stage=stage.get("next"),
                    delay=stage.get("delay"),
                )
            else:
                # Завершить задачу
                await self.to_stage(
                    from_stage=stage_name, workflow_id=workflow_id
                )
        else:
            logger.warning(
                f"Неизвестный этап workflow: {stage_name} в воронке: {self.get_workflow()}"  # noqa
            )


# ─────────────────────────────────────────────────────────────────────────────
# 📅 Конкретные события cron
# ─────────────────────────────────────────────────────────────────────────────


class ScheduleReport(CronBaseClass):
    """
    Событие для формирования и отправки отчетов клиентам или администраторам по расписанию.

    Данные в `self.data` должны содержать информацию для генерации отчета:
    - получатели (chat_id, client_id)
    - шаблоны сообщений
    - параметры для рендеринга
    """


class ReactivationClient(WorkflowBase):
    """
    Workflow для реактивации спящих клиентов студии йоги.

    Этапы воронки:
        1. Мягкое напоминание
        2. Персональное предложение
        3. Срочное напоминание
        4. Прощальное сообщение
        5. Анализ и сегментация

    Каждый этап автоматически запускает следующий с задержкой (например, "30s", "2d").
    """


class FirstClientVisit(WorkflowBase):
    """Отправить сообщение клиенту о первой тренировке"""
