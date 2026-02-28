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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

from pydantic import Field, ConfigDict

from micro.models.header_event import HeaderEvent
from micro.pg_ext import fetchone, execute, returning, select

from micro.utils import str_to_timedelta, parse_time_and_adjust
from micro.send_messages import send_message

# Настройка логгера
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 🧱 Базовые классы
# ─────────────────────────────────────────────────────────────────────────────


class CronBaseClass(HeaderEvent):
    """
    Базовый класс для всех событий, запускаемых по расписанию (cron).

    Предоставляет структуру для хранения списка данных,
    которые будут обработаны.
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

    model_config = ConfigDict()

    _workflow_id: Optional[int] = None

    _js: Optional[dict] = None

    _stage: Optional[str] = None

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
        :return: Название текущего этапа или None,
        если этап не найден или данные некорректны.
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
        if not self._stage:
            self._stage = self.data.get("stage")
            if not self._stage:
                raise ValueError(f"Не задан stage в поле data: {self.data}")
        return self._stage

    @property
    def capture_stage(self) -> Optional[str]:
        """
        Возвращает стартовое событие перехода,
        хранится в словаре self.data

        :return Optional[str]: _description_
        """
        return self.get_stage()

    def set_capture_stage(self, value):
        self._stage = value

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
                    "Параметр 'delay' должен быть строкой или объектом timedelta"  # noqa
                )
        return delay_timedelta

    async def update_sql(self, data: list):
        current_timestamp = datetime.now()
        return {
            "sql": """
                    UPDATE workflow_stages
                    SET executed_at = %(current_timestamp)s,
                        data = %(data)s
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
                # Сохранить результат выполнения stage
                "data": json.dumps(data, ensure_ascii=True),
            },
        }

    async def insert_sql(
        self, from_stage: str, to_stage: str, delay: str, time_str: str
    ):
        current_timestamp = datetime.now()
        started_at = current_timestamp
        # Вычислить время запуска нового состояния
        # Преобразование строки в timedelta, если необходимо
        if delay:
            delay_timedelta: Optional[timedelta] = self.delay2timedelta(delay)
            started_at = current_timestamp + delay_timedelta
        if time_str:
            started_at = parse_time_and_adjust(
                base_datetime=started_at, time_str=time_str
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
        data: list,
        to_stage: Optional[str] = None,
        delay: Optional[str | timedelta] = None,
        time_str: Optional[str] = None,
    ) -> None:

        logger.info(
            f'Смена этапа "{self.capture_stage}" '
            + f'-> "{to_stage}", delay: "{delay} {time_str}"'
        )

        # SQL-операции: завершить текущий этап(ы)
        sql_operations = [await self.update_sql(data=data)]

        # Если stage не задан, то считаем, что только завершить текущий stage
        # Добавить в SQL создать новую задачу
        if to_stage:
            sql_operations += [
                await self.insert_sql(
                    from_stage=self.capture_stage,
                    to_stage=to_stage,
                    delay=delay,
                    time_str=time_str,
                )
            ]

        # Выполняем все операции в одной транзакции
        await execute(query=sql_operations)
        logger.info(f"Этап workflow успешно обновлен: {to_stage or 'закрыт'}")

    async def break_rules(self, conditions: list):
        # Первое же удачное условие вызывает переход !!!
        for condition in conditions:
            logger.info(f"test condition: {condition}")
            # Выполнить SQL запрос
            data = await select(condition.get("file"), params=self.js)
            if data and condition.get("then"):
                self.set_capture_stage(condition.get("then"))
                logger.info(f"goto {self.capture_stage}")
                break
            elif not data and condition.get("else"):
                self.set_capture_stage(condition.get("else"))
                logger.info(f"goto {self.capture_stage}")
                break

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
            logger.info(
                f'Включен режим отладки для workflow "{self.workflow}"'
            )

        # Правила прерывание workflow
        if rules.get("break"):
            await self.break_rules(rules.get("break"))

        # Получить задачи workflow
        stages = rules.get("stages", {})
        # Получить текущую задачу
        stage = stages.get(self.capture_stage)
        if stage:
            # Выполнить SQL запрос
            data = []
            if stage.get("file"):
                data = await select(
                    stage.get("file"),
                    params=self.js,
                    template_path=f"templates/{self.workflow}",
                )
            # Отправить сообщение клиенту и администратору
            info = {
                "workflow_id": "#" + str(await self.workflow_id()),
                "workflow": self.workflow,
                "capture_stage": self.capture_stage,
                "desc": stage.get("desc", "-"),
                "delay": stage.get("delay", "-"),
                "data": data,
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
                    time_str=stage.get("time"),
                    data=data,
                )
            else:
                # Завершить задачу, есди не задана новая
                await self.new_stage(
                    data=data,
                )
        else:
            logger.warning(
                f'Неизвестный этап "{self.capture_stage}" в workflow "{self.workflow}"'  # noqa
            )


# ─────────────────────────────────────────────────────────────────────────────
# 📅 Конкретные события cron
# ─────────────────────────────────────────────────────────────────────────────


class ScheduleReport(CronBaseClass):
    """
    Событие для формирования и отправки отчетов клиентам
    или администраторам по расписанию.

    Данные в `self.data` должны содержать информацию для генерации отчета:
    - получатели (chat_id, client_id)
    - шаблоны сообщений
    - параметры для рендеринга
    """


class OpenWorkflow(CronBaseClass):
    """
    Запустить workflow, cron обработчиком
    исходные данные лежат в поле дата
    """

    pass


class CloseWorkflow(HeaderEvent):
    """Закрыть заданный workflow"""

    workflow_id: int | None = Field(
        None, description="Идентификатор workflow"
    )  # noqa


class CreateStage(HeaderEvent):
    """Создать задачу в workflow"""

    workflow_id: int | None = Field(
        None, description="Идентификатор workflow"
    )  # noqa
    stage_name: str | None = Field(
        None, description="Наименование stage задачи"
    )  # noqa
    stage_id: int | None = Field(
        None,
        description="Идентификатор текущей задачи, которая запустила новую",
    )  # noqa


class StartStage(CronBaseClass):
    """Выполнить задачу, cron обработчиком
    исходные данные лежат в поле дата
    """

    pass


class CheckWorkflow(CronBaseClass):
    """Проверить workflow
    Выполнить проверку и сделать переход на определенный stage
    исходные данные лежат в поле дата
    """

    pass


class UpdateBudget(CronBaseClass):
    """Отправить событие пересчитать бюджет"""

    pass


class HourPassed(CronBaseClass):
    """Отправить событие каждый час"""

    ...


class TwoHoursPassed(CronBaseClass):
    """Отправить событие каждые 2 часа"""

    ...


class MidnightReached(CronBaseClass):
    """Отправить событие каждые сутки в 00 часов"""

    ...


class CronTriggeredEvent(HeaderEvent):
    """Запустилось событие cron"""

    # fmt: off
    id: int | None = Field(None, description="Уникальный идентификатор задачи")
    name: str | None = Field(None, description="Отображаемое имя задачи")
    cron: str | None = Field(None, description="Cron-выражение, определяющее расписание задачи (например, '0 9 * * *')",) # noqa
    func: str = Field(..., description="Полный путь до вызываемой функции (например, 'app.jobs.send_email')") # noqa
    args: Dict[str, Any] | None = Field(None, description="Аргументы, передаваемые в функцию при выполнении задачи",)  # noqa
    last_fire_time: datetime | None = Field(None, description="Дата и время последнего выполнения задачи") # noqa
    next_fire_time: datetime | None = Field(None, description="Дата и время следующего запланированного запуска задачи",) # noqa
    timezone: str | None = Field(default=None, description="Timezone")
    # fmt: on

    def route_key(self):
        return f"cron:{self.id}"


class EmailCheckScheduled(CronBaseClass):
    """Нужно проверить почту"""

    ...


class LegacyCronTriggeredEvent(CronBaseClass):
    """schedule.do обработка"""

    ...


class ChannelTestTriggered(CronBaseClass):
    """Наступило время проверки входных каналов сообщений"""

    ...
