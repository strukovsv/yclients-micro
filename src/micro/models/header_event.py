from __future__ import annotations

import logging

import datetime

from typing import Any, List, Optional, Union

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

from micro.kafka_producer import KafkaProducer

import micro.config as config

logger = logging.getLogger(__name__)


class Header(BaseModel):
    # fmt: off
    event: str | None = Field(None, description="Имя сообщения") # noqa
    uuid: str | None = Field(None, description="Идентификатор сообщения") # noqa
    parent: str | None = Field(None, description="Идентификатор родительского сообщения") # noqa
    root: str | None = Field(None, description="Идентификатор цепочки сообщений") # noqa
    desc: str | None = Field(None, description="Описание сообщения") # noqa
    version: str | None = Field(None, description="Версия сообщения") # noqa
    source: str | None = Field(None, description="Источник сообщения") # noqa
    # fmt: on


class Addresse(BaseModel):
    """Адрессат сообщения"""

    # fmt: off
    client_id: str | None = Field(None, description="Получатель сообщения в yclients SMS") # noqa
    chat_id: str | None = Field(None, description="Получатель сообщения в telegram") # noqa
    # fmt: on


class HeaderEvent(AvroBase):
    # fmt: off
    header: Header | None = Field(None, description="Заголовок сообщения") # noqa
    addresse: Addresse | None = Field(None, description="Получатель сообщения") # noqa
    # fmt: on

    def route_key(self):
        return (
            self.addresse.chat_id
            or self.addresse.client_id
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
        parent: object = None,
    ) -> None:
        """Отправить объект в поток

        :param HeaderEvent obj: объект
        :param any key: route key для topic, defaults to None
        :param str chain_uuid: цепочка сообщений
        :param str desc: описание события
        :param str version: версия события
        :param str client_id: отправить сообщение через Yclients SMS
        :param str chat_id: отправить сообщение через telegram
        """
        # Дата сообщения
        now = datetime.datetime.now()
        # Заголовок сообщения
        self.header = Header(
            # Тип события, как название класса
            event=self.__class__.__name__,
            # идентификатор текущего события
            uuid=config.PRODUCER_ID + "-" + now.isoformat(),
            # Описание события
            desc=desc,
            # Версия события
            version=version,
            # источник сообщения
            source=config.PRODUCER_ID,
        )
        # Получатель сообщения
        self.addresse = addresse or Addresse(
            client_id=client_id, chat_id=chat_id
        )
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
        # logger.info(f'{parent=}')
        # logger.info(f'{self.header=}')
        # Отправить сообщение, если не задан ключ,
        # то взять от даты псевдослучайное число
        await KafkaProducer().send_kafka(
            key=key or self.route_key(), data=self.dict()
        )
        logger.info(f'send object "{self.header.event}"')


class PrintBaseEvent(HeaderEvent):
    """Базовые отчеты для сотрудника и для админа"""

    # fmt: off
    # yesterday, now, tomorrow, prev-week, week, next-week, prev-month, month, next-month, YYYYMMDD
    period: str = Field(..., description="Период формирования отчета")  # noqa
    staff: str | None = Field(None, description="Сотрудник")  # noqa
    # fmt: on
