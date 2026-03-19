from __future__ import annotations

import logging

import datetime
from datetime import UTC
import uuid

from pydantic import Field, BaseModel

from micro.kafka_producer import KafkaProducer
from micro.logging_trace import TRACE

import micro.config as config

logger = logging.getLogger(__name__)


class Header(BaseModel):
    """
    Заголовок события Kafka — метаинформация для трассировки и маршрутизации.

    Attributes:
        utc: Время события в UTC (ISO 8601).
        datetime: Локальное время события (ISO 8601).
        event: Имя класса-события, используется как тип сообщения.
        uuid: Уникальный идентификатор события (UUID v4).
        parent: UUID родительского события (для цепочек вызовов).
        root: UUID корневого события в цепочке (сквозной trace_id).
        desc: Человеко-читаемое описание события.
        version: Версия схемы события (semver).
        source: Идентификатор источника (PRODUCER_ID из конфига).
    """

    # fmt: off
    utc: str | None = Field(None, description="Время сообщения в формате UTC") # noqa
    datetime: str | None = Field(None, description="Время сообщения") # noqa
    event: str | None = Field(None, description="Имя сообщения") # noqa
    uuid: str | None = Field(None, description="Идентификатор сообщения") # noqa
    parent: str | None = Field(None, description="Идентификатор родительского сообщения") # noqa
    root: str | None = Field(None, description="Идентификатор цепочки сообщений") # noqa
    desc: str | None = Field(None, description="Описание сообщения") # noqa
    version: str | None = Field(None, description="Версия сообщения") # noqa
    source: str | None = Field(None, description="Источник сообщения") # noqa
    trace_id: str | None = Field(None, description="Цепочка сообщений") # noqa
    # fmt: on


class Addresse(BaseModel):
    """
    Адресат сообщения — определяет канал доставки.

    Attributes:
        client_id: ID клиента для отправки через Yclients SMS.
        chat_id: ID чата для отправки через Telegram.
        channel: ID канала/группы для отправки через Telegram.
    """

    # fmt: off
    client_id: str | None = Field(None, description="Получатель сообщения в yclients SMS") # noqa
    chat_id: str | None = Field(None, description="Получатель сообщения в telegram") # noqa
    channel: str | None = Field(None, description="Идентификатор канала или группы в telegram") # noqa
    contact_id: str | None = Field(None, description="Идентификатор lead или клиента во внешней системе") # noqa
    # fmt: on


class HeaderEvent(BaseModel):
    """
    Базовый класс события с заголовком и адресатом.

    Предоставляет методы для формирования метаданных, маршрутизации
    и отправки в Kafka. Используется как основа для конкретных событий.

    Attributes:
        header: Метаинформация события (экземпляр Header).
        addresse: Адресат доставки (экземпляр Recipient).
    """

    # fmt: off
    header: Header | None = Field(None, description="Заголовок сообщения") # noqa
    addresse: Addresse | None = Field(None, description="Получатель сообщения") # noqa
    # fmt: on

    def route_key(self):
        """
        Формирует ключ маршрутизации для Kafka topic partition.

        Priority: chat_id → client_id → channel → PRODUCER_ID → "na".

        Returns:
            str: Строковый ключ для шардирования.
        """
        return (
            self.addresse.chat_id
            or self.addresse.client_id
            or self.addresse.channel
            or self.addresse.contact_id
            or config.PRODUCER_ID
            or "na"
        )

    async def deserialization(self):
        """Абстрактный метод десереализации"""
        pass

    async def send(
        self,
        key: any = None,
        desc: str = None,
        version: str = None,
        client_id: str = None,
        addresse: Addresse = None,
        chat_id: str = None,
        channel: str = None,
        contact_id: str = None,
        parent: object = None,
        topic: str = None,
    ) -> None:
        """
        Отправляет событие в Kafka с авто-генерацией заголовка.

        Формирует Header (uuid, timestamps, trace-chain) и Recipient,
        затем сериализует объект и отправляет через KafkaProducer.

        Args:
            key: Ключ маршрутизации (переопределяет route_key()).
            desc: Описание события (перезаписывает поле в header).
            version: Версия схемы события.
            client_id: ID клиента для Yclients SMS (альтернатива addresse).
            addresse: Готовый объект Recipient
              (приоритет над отдельными полями).
            chat_id: ID Telegram-чата (если не задан addresse).
            channel: ID Telegram-канала (если не задан addresse).
            parent: Родительское событие для построения цепочки (parent/root).

        Returns:
            None

        Side Effects:
            - Отправляет сообщение в Kafka.
            - Логгирует факт отправки.
            - Модифицирует self.header и self.addresse.
        """
        # Дата сообщения
        now_utc = datetime.datetime.now(UTC)
        now_local = datetime.datetime.now()
        # Заголовок сообщения
        self.header = Header(
            # Время события в utc
            utc=now_utc.isoformat(),
            # Локальное время события
            datetime=now_local.isoformat(),
            # Тип события, как название класса
            event=self.__class__.__name__,
            # идентификатор текущего события
            uuid=str(uuid.uuid4()),
            # Описание события
            desc=desc,
            # Версия события
            version=version,
            # источник сообщения
            source=config.PRODUCER_ID,
            # Идентификатор trace_id
            trace_id=TRACE().trace_id,
        )
        # Получатель сообщения
        self.addresse = addresse or Addresse(
            client_id=client_id,
            chat_id=chat_id,
            channel=channel,
            contact_id=contact_id,
        )
        # Строим цепочку сообщений (distributed tracing)
        # Сформировать атрибут для цепочки сообщений
        # Если задан родитель в отправке, то из него взять значение
        self.header.root = (
            parent.header.root
            if parent and hasattr(parent.header, "root")
            else self.header.uuid
        )
        # Взять родителя сообщения, если первое сообщение в цепочке,
        # то родителя не ставим
        self.header.parent = (
            parent.header.uuid
            if parent and hasattr(parent.header, "uuid")
            else None
        )
        # Отправить сообщение, если не задан ключ,
        # то взять от даты псевдослучайное число
        await KafkaProducer().send_kafka(
            key=key or self.route_key(), data=self.dict(), topic=topic
        )
        logger.info(
            f'send event "{self.header.event}" with uuid={self.header.uuid}'
        )


class PrintBaseEvent(HeaderEvent):
    """Базовое событие для генерации отчетов (сотрудник/админ).

    Содержит параметры периода и привязки к сотруднику для фильтрации.
    period: yesterday, now, tomorrow, prev-week, week, next-week,
            prev-month, month, next-month, YYYYMMDD
    """

    # fmt: off
    period: str = Field(..., description="Период формирования отчета")  # noqa
    staff: str | None = Field(None, description="Сотрудник")  # noqa
    # fmt: on
