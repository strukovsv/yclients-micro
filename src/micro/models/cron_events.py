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
from micro.pg_ext import fetchone, execute, returning

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


class Workflow(CronBaseClass):
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
                "ident_id": 304734851,
                "client_id": 272696997,
                "client_name": "+79135602444 Дарья",
                "last_training_date": datetime.date(2025, 8, 11),
                "current_record_date": None,
                "cards": None,
            }
        ]
    """

    _workflow_id: Optional[int] = None

    _js: Optional[dict] = None

    class Config:
        underscore_attrs_are_private = True

    def get_event(self) -> Optional[str]:
        """
        Получить имя класса,
        для данного объекта это будет Workflow
        """
        return self.__class__.__name__

    @property
    def event(self) -> Optional[str]:
        """
        Получить имя класса,
        для данного объекта это будет Workflow
        """
        return self.get_event()

    def get_js(self) -> dict:
        """
        Получает текущий активный этап workflow из базы данных.
        :return: Название текущего этапа или None, если этап не найден или данные некорректны.
        """
        if self._js:
            return self._js
        else:
            _js = self.data.get("js", self.data).copy()
            # Удалить состояние что-бы не смущала
            _js.pop("stage", None)
            return _js

    @property
    def js(self) -> dict:
        return self.get_js()

    def get_workflow(self) -> str:
        """
        Получить имя workflow

        exammple: first_client_visit, reactivation_client

        :return str: workflow
        """
        _ = self.data.get("workflow", None)
        if not _:
            raise ValueError(f"Не задан workflow в поле data: {self.data}")
        return _

    @property
    def workflow(self):
        """
        Получить имя workflow

        exammple: first_client_visit, reactivation_client

        :return str: workflow
        """
        return self.get_workflow()

    def get_ident_id(self) -> str:
        """
        Получить идентификатор события,
        сохраняется в словаре self.data
        а также прописывается в таблицу workflow_stages.ident_id

        :return str: идентификатор события
        """
        _ = str(self.js.get("ident_id"))
        if not _:
            raise ValueError(f"Не задан ident_id в поле data: {self.js}")
        return _

    @property
    def ident_id(self) -> str:
        """
        Получить идентификатор события,
        сохраняется в словаре self.data
        а также прописывается в таблицу workflow_stages.ident_id

        :return str: идентификатор события
        """
        return self.get_ident_id()

    def get_stage(self) -> Optional[str]:
        """
        Возвращает стартовое событие перехода,
        хранится в словаре self.data

        :return Optional[str]: _description_
        """
        _ = self.data.get("stage")
        if not _:
            raise ValueError(f"Не задан stage в поле data: {self.data}")
        return _

    @property
    def capture_stage(self) -> Optional[str]:
        """
        Возвращает стартовое событие перехода,
        хранится в словаре self.data

        :return Optional[str]: _description_
        """
        return self.get_stage()

    async def insert_into_workflow(self) -> int:
        """
        Добавить запись в таблицу workflow и вернуть идентификатор
        """
        workflow = await returning(
            """insert into workflow (moment) values (now()) returning id"""
        )
        return workflow.get("id")

    async def get_workflow_id(self) -> int:
        """
        Получить workflow_id для текущего активного задания
        """
        stage = await fetchone(
            """
SELECT workflow_id
FROM workflow_stages
WHERE event = %(event)s
  AND workflow = %(workflow)s
  AND ident_id = %(ident_id)s
  AND executed_at IS NULL""",
            {
                # Получить имя воронки, процесса
                "event": self.event,
                # Получить имя воронки, процесса
                "workflow": self.workflow,
                # Идентификатор, уникальность воронки
                "ident_id": self.ident_id,
            },
        )
        return stage.get("workflow_id") if stage else None

    async def workflow_id(self):
        if not self._workflow_id:
            self._workflow_id = await self.get_workflow_id()
            if not self._workflow_id:
                self._workflow_id = await self.insert_into_workflow()
        return self._workflow_id

    def delay2timedelta(self, delay: Optional[str | timedelta]) -> timedelta:
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
        return delay_timedelta

    async def update_sql(self):
        current_timestamp = datetime.now()
        return {
            "sql": """
                    UPDATE workflow_stages
                    SET executed_at = %(current_timestamp)s
                    WHERE event = %(event)s
                      AND workflow = %(workflow)s
                      AND ident_id = %(ident_id)s
                      AND executed_at IS NULL
                """,
            "params": {
                # Получить имя воронки, процесса
                "event": self.event,
                "workflow": self.workflow,
                # Идентификатор, уникальность воронки
                "ident_id": self.ident_id,
                # Простамить текущее время
                "current_timestamp": current_timestamp,
            },
        }

    async def insert_sql(self, from_stage: str, to_stage: str, delay: str):
        current_timestamp = datetime.now()
        # Вычислить время запуска нового состояния
        # Преобразование строки в timedelta, если необходимо
        delay_timedelta: Optional[timedelta] = self.delay2timedelta(delay)
        started_at = (
            current_timestamp + delay_timedelta
            if delay_timedelta
            else current_timestamp
        )
        return {
            "sql": """
INSERT INTO workflow_stages (
    event,
    workflow,
    ident_id,
    from_stage,
    stage,
    created_at,
    started_at,
    js,
    workflow_id
) VALUES (
    %(event)s,
    %(workflow)s,
    %(ident_id)s,
    %(from_stage)s,
    %(stage)s,
    %(current_timestamp)s,
    %(started_at)s,
    %(js)s,
    %(workflow_id)s
)
                    """,
            "params": {
                # Идентификаторы задачи
                "event": self.event,
                "workflow": self.workflow,
                "ident_id": self.ident_id,
                # Предыдущее состояние
                "from_stage": from_stage,
                # Новое состояние
                "stage": to_stage,
                # Запустить в заданное время
                "started_at": started_at,
                # Текущее время, для создания задачи
                "current_timestamp": current_timestamp,
                # Данные задания, контекст
                "js": json.dumps(self.js, ensure_ascii=True),
                # Идентификатор workflow_id
                "workflow_id": await self.workflow_id(),
            },
        }

    async def new_stage(
        self,
        to_stage: Optional[str] = None,
        delay: Optional[str | timedelta] = None,
    ) -> None:

        logger.info(
            f'Смена этапа "{self.capture_stage}" -> "{to_stage}", delay: "{delay}"'
        )

        # SQL-операции: завершить текущий этап(ы)
        sql_operations = [await self.update_sql()]

        # Если stage не задан, то считаем, что только завершить текущий stage
        # Добавить в SQL создать новую задачу
        if to_stage:
            sql_operations += [
                await self.insert_sql(
                    from_stage=self.capture_stage,
                    to_stage=to_stage,
                    delay=delay,
                )
            ]

        # Выполняем все операции в одной транзакции
        await execute(query=sql_operations)
        logger.info(f"Этап workflow успешно обновлен: {to_stage or 'закрыт'}")

    async def stage_worker(
        self,
        load_stages,
    ):
        logger.info(
            f'Start workflow "{self.workflow=}" :: "{self.capture_stage}"'
        )
        # Идентификатор, уникальность воронки
        # Проинициализировать workflow
        await self.workflow_id()
        # Загрузить описание задач, из yaml
        rules = load_stages(workflow_name=self.workflow)
        # Получить флаг отладки workflow
        debug = rules.get("debug", False)
        if debug:
            logger.info(f'Включен режим отладки для workflow "{self.workflow}"')
        # Получить задачи workflow
        stages = rules.get("stages", {})
        # Получить текущую задачу
        stage = stages.get(self.capture_stage)
        if stage:
            # Отправить сообщение клиенту и администратору
            info = {
                "workflow_id": "#" + str(await self.workflow_id()),
                "workflow": self.workflow,
                "capture_stage": self.capture_stage,
                "desc": stage.get("desc", "-"),
                "delay": stage.get("delay", "-"),
            }
            await send_message(
                workflow=self.workflow,
                stage=self.capture_stage,
                debug=debug,
                data={**self.js, **{"info": info}},
            )
            # Если задан, то запустить следующий этап с задержкой
            if stage.get("next"):
                await self.new_stage(
                    to_stage=stage.get("next"),
                    delay=stage.get("delay"),
                )
            else:
                # Завершить задачу, есди не задана новая
                await self.new_stage()
        else:
            logger.warning(
                f'Неизвестный этап "{self.capture_stage}" в workflow "{self.workflow}"'  # noqa
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


# class Workflow(WorkflowBase):
#     """Базовый workflow"""


# class ReactivationClient(WorkflowBase):
#     """
#     Workflow для реактивации спящих клиентов студии йоги.

#     Этапы воронки:
#         1. Мягкое напоминание
#         2. Персональное предложение
#         3. Срочное напоминание
#         4. Прощальное сообщение
#         5. Анализ и сегментация

#     Каждый этап автоматически запускает следующий с задержкой (например, "30s", "2d").
#     """


# class FirstClientVisit(WorkflowBase):
#     """Отправить сообщение клиенту о первой тренировке"""
