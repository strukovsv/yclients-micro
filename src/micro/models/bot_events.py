from __future__ import annotations

import logging
from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

from micro.models.header_event import HeaderEvent

logger = logging.getLogger(__name__)


# Промежуточный класс
class MenuItem:
    title: str
    callback_data: str
    data: str | None
    query: str | None

    def __init__(
        self, title, callback_data, data: str = None, query: str = None
    ):
        self.title = title
        self.callback_data = callback_data
        self.data = data
        self.query = query


class TelegramUser(BaseModel):
    """Пользователь в telegram"""

    id: int  # noqa
    name: str  # noqa
    first_name: str  # noqa
    last_name: str  # noqa
    telegram_id: str  # noqa
    telegram_username: str  # noqa
    client_id: int | None  # noqa
    staff_id: int | None  # noqa
    access: List[str] | None  # noqa
    password: str | None  # noqa
    phone: str | None  # noqa
    staff: str | None

    def acc(self, tp_list: any) -> bool:
        """Проверить уровень доступа"""
        for item in tp_list if isinstance(tp_list, list) else [tp_list]:
            if item in self.access:
                return True
        return False


class BotBaseClass(HeaderEvent):
    user: TelegramUser  # noqa

    def route_key(self):
        return self.user.telegram_id


class BotEnteredTextMessage(BotBaseClass):
    """Введен текст в боте"""

    text: str  # noqa
    message_id: int  # noqa


class BotEnteredReplyMessage(BotBaseClass):
    """Введен ответ на текст в боте"""

    text: str  # noqa
    message_id: int  # noqa
    reply_text: str  # noqa
    reply_message_id: int  # noqa


class BotCallback(BotBaseClass):
    """Выбран пункт меню"""

    MAX_ELEMENTS_IN_CALLBACK: int = 5

    data: str
    message_id: int  # noqa

    def get_callback(self) -> list:
        """Разбить callback ответ на элементы"""
        callback_data = []
        callback_data_list = self.data.split(".")
        for index in range(0, self.MAX_ELEMENTS_IN_CALLBACK):
            callback_data.append(
                callback_data_list[index]
                if len(callback_data_list) > index
                else None
            )
        return callback_data

    def last(self) -> str:
        """Последнее значение в списке"""
        elements = self.data.split(".")
        if elements:
            return elements[len(elements) - 1]
        else:
            # Пустой список callback
            return None

    def prev(self) -> str:
        """Отрезать последний элементов списке"""
        elements = self.data.split(".")
        elements.pop()
        return ".".join(elements)


class BotEnteredCommand(BotBaseClass):
    """Введена команда"""

    command: str
    message_id: int  # noqa


class EventMenuItem(BaseModel):
    """Item меню бота"""

    item_name: str = Field(
        ..., description="Наименование элемента меню"
    )  # noqa
    callback_data: str = Field(
        ..., description="Код возврата при выборе элемента"
    )  # noqa


class BotSendBase(HeaderEvent):
    """Послать боту меню"""

    telegram_id: int = Field(
        ..., description="Идентификатор user в telegram"
    )  # noqa

    def route_key(self):
        return self.telegram_id


class BotSendCalendar(BotSendBase):
    # fmt: off
    """Послать боту команду, показать календарь"""
    prefix: str = Field(..., description="Префикс callback")  # noqa
    query: str | None = Field(None, description='Вопрос выбора в меню, по умолчанию "Choose :"')  # noqa
    # fmt: on


class BotSendMenu(BotSendBase):
    """Послать боту меню"""

    # fmt: off
    items: List[EventMenuItem] = Field(..., description="Список items в меню")  # noqa
    query: str | None = Field(None, description='Вопрос выбора в меню, по умолчанию "Choose :"')  # noqa
    row_width: int | None = Field(None, description="Кол-во элементов в строке меню, по умолчанию 1")  # noqa
    update: bool | None = Field(None, description="Обновить последний элемент меню")  # noqa
    # fmt: on

    async def send_menu(
        telegram_id: int,
        items: list,
        query: str = None,
        row_width: int = None,
        chain_uuid: str = None,
        prefix: str = None,
        update: bool = False,
    ):
        """Отправить сообщение на создание меню в боте

        :param int telegram_id: идентификтор пользователя
        :param list items: список элементов меню (title, callback_data)
        :param str query: Текст запроса меню, defaults to None
        :param int row_width: Кол-во элементов в строке, defaults to None
        :param str chain_uuid: идентификатор цепочки сообщений, defaults to None
        """
        # Создать сообщение отправить меню
        await BotSendMenu(
            # идентификтор получателя в telegram
            telegram_id=telegram_id,
            # Элементы меню
            items=[
                EventMenuItem(
                    item_name=item.title,
                    callback_data=(
                        (
                            f"{prefix}.{item.callback_data}"
                            if prefix
                            else f'{item.callback_data}{item.callback_data2}'
                        )
                        # + f".{item.callback_data2}"
                        # if item.callback_data2
                        # else ""
                    ),
                )
                for item in items
            ],
            # Вопрос в меню
            query=query if query else "Выберите?",
            # Кол-во элементов в строке
            row_width=row_width,
            update=update,
        ).send()

    async def send_menu_items(
        obj,
        items: list,
        prefix: str = None,
        query: str = None,
        row_width: int = 3,
    ):
        await BotSendMenu.send_menu(
            telegram_id=obj.user.telegram_id,
            items=items,
            chain_uuid=obj.header.chain_uuid,
            row_width=row_width,
            query=query,
            prefix=prefix,
        )

    async def send_menu_elem(
        obj,
        elements: list,
        prefix: str = None,
        query: str = None,
        row_width: int = 3,
        update: bool = False,
    ):
        items = []
        logger.info(f"{elements=}")
        for id, name in elements:
            items.append(MenuItem(name, str(id)))
        await BotSendMenu.send_menu(
            telegram_id=obj.user.telegram_id,
            items=items,
            chain_uuid=obj.header.chain_uuid,
            row_width=row_width,
            query=query,
            prefix=prefix,
            update=update,
        )


class BotSendText(BotSendBase):
    """Послать сообщение боту"""

    text: str | List[str] = Field(
        None, description="Текс сообщения или массив сообщений"
    )  # noqa

    # def __init__(
    #     telegram_id: int,
    #     text: str = None,
    # ):
    #     """Отправить сообщение в бот

    #     :param int telegram_id: идентификтор пользователя
    #     :param str text: Текст сообщения
    #     """
    #     self.t
    #     # Послать сообщение сообщение отправить меню
    #     await BotSendText(
    #         # идентификтор получателя в telegram
    #         telegram_id=telegram_id,
    #         # Текст сообщения
    #         text=text,
    #     ).send()
