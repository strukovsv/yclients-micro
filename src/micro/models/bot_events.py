from __future__ import annotations

import logging
from typing import List

from pydantic import Field, BaseModel

import micro.pg_ext as base
import micro.config as config

from micro.models.header_event import HeaderEvent

logger = logging.getLogger(__name__)


class TelegramUser2(BaseModel):
    id: int  # noqa
    first_name: str  # noqa
    last_name: str | None  # noqa
    username: str | None  # noqa
    language_code: str  # noqa


class TelegramMessageReceived(HeaderEvent):
    user: TelegramUser2
    chat_id: int
    text: str
    message_id: int
    reply_text: str | None
    reply_message_id: int | None
    topic_id: int | None


class TelegramCallbackReceived(HeaderEvent):
    # Принято сообщение из канала telegram
    user: TelegramUser2
    chat_id: int
    text: str
    data: str
    message_id: int


class TelegramUser(BaseModel):
    """Пользователь в telegram message.from_user"""

    id: str  # noqa
    first_name: str  # noqa
    last_name: str | None  # noqa
    username: str | None  # noqa
    language_code: str  # noqa
    channel: str | None  # noqa
    chat_id: str | None  # noqa

    access: list | None = []  # noqa

    def __init__(self, **kwarg):
        super().__init__(
            id=str(kwarg["id"]),
            first_name=kwarg["first_name"],
            last_name=kwarg["last_name"],
            username=kwarg["username"],
            language_code=kwarg["language_code"],
            channel=kwarg["channel"],
            chat_id=kwarg["chat_id"],
        )

    def acc(self, tp_list: any) -> bool:
        """Проверить уровень доступа"""
        for item in tp_list if isinstance(tp_list, list) else [tp_list]:
            if item in self.access:
                return True
        return False

    async def fill_access(self) -> list:
        # Вернуть запись из таблицы
        for user in await base.fetchall(
            "select * from passwd p where p.telegram_id = %(id)s",
            {"id": self.id},
        ):
            # Запрос
            # logger.info(f"get access from: {user}")
            # Вернуть массив доступа, убрать пробелы
            self.access = [acc.strip() for acc in user["access"].split(",")]

    async def get_staff(self) -> list:
        # Вернуть запись из таблицы
        for user in await base.fetchall(
            "select * from passwd p where p.telegram_id = %(id)s",
            {"id": self.id},
        ):
            # Запрос
            # logger.info(f"get access from: {user}")
            # Вернуть массив доступа, убрать пробелы
            return user["first_name"]
        return None

    async def fill(self) -> list:
        """Найти в таблице пользователя, если нет создать"""
        if (
            await base.fetchone(
                "select * from passwd p where p.telegram_id = %(id)s",
                {"id": self.id},
            )
            is None
        ):
            logger.info(f"new telegram user: {self.username}")
            # Запомнить нового пользователя в таблице
            await base.execute(
                """
insert into passwd
(name, first_name, last_name, telegram_id,
  telegram_username, access, chat_id, channel)
values
(%(username)s, %(first_name)s, %(last_name)s, %(id)s,
  %(username)s, 'user', %(chat_id)s, %(channel)s)
        """,
                self.__dict__,
            )
        # Заполнить уровни доступа
        await self.fill_access()

    async def get_chat_id_for_access(access: str) -> list:
        """Найти пользователей telegram с заданным уровнем доступа"""
        result = await base.fetchall(
            f"""
select p.telegram_id
from passwd p
where concat(',', lower(replace(p.access, ' ', '')), ',')
like '%,{access.strip().lower()},%'""",
        )
        logger.info(f"get_chat_id_for_access: {result=}")
        return [int(user["telegram_id"]) for user in result]


class BotBaseClass(HeaderEvent):
    """Базовое сообщение для бота"""

    chat_id: str

    def route_key(self):
        return f"{self.chat_id}"


class BotEnteredClass(BotBaseClass):
    """Базовое сообщение полученное от бота"""

    # Данные о пользователе, какие получены из telegram api
    user: TelegramUser  # noqa

    # fmt: off
    history: list | None = Field(None, description="История отправленных сообщений в диалоге")  # noqa
    # fmt: on

    async def deserialization(self):
        """Загрузить данные о пользователе из БД
        , если нет записи, то создать нового пользователя
        , получить уровни доступа из БД"""
        await self.user.fill()
        # Вызвать метод предок
        await super().deserialization()

    def last_stage(self) -> str:
        """Вернуть stage последний отправленный клиенту"""
        if self.history:
            return self.history[len(self.history) - 1].get("stage", None)
        else:
            return None

    def last_data(self) -> str:
        """Вернуть data последний отправленный клиенту"""
        if self.history:
            return self.history[len(self.history) - 1].get("data", {})
        else:
            return {}


class BotEnteredTextMessage(BotEnteredClass):
    """Введен текст в боте"""

    text: str  # noqa


class BotEnteredReplyMessage(BotEnteredClass):
    """Введен ответ на текст в боте"""

    text: str  # noqa
    reply_text: str | None  # noqa


class BotCallback(BotEnteredClass):
    """Выбран пункт меню"""

    MAX_ELEMENTS_IN_CALLBACK: int = 5

    data: str


class BotEnteredCommand(BotEnteredClass):
    """Введена команда"""

    command: str


class EventMenuItem(BaseModel):
    """Item меню бота"""

    # fmt: off
    item_name: str = Field(..., description="Наименование элемента меню")  # noqa
    callback_data: str = Field(..., description="Код возврата при выборе элемента")  # noqa
    # fmt: on


class BotSendBase(HeaderEvent):
    """Послать боту меню"""

    # fmt: off
    chat_id: int = Field(..., description="Идентификатор чата в telegram")  # noqa
    history: list | None = Field(None, description="История отправленных сообщений в диалоге")  # noqa
    # fmt: on

    def route_key(self):
        return f"{self.chat_id}"

    def add(self, stage: str = "stage", data: any = None):
        """Добавить в историю сообщение"""
        if self.history is None:
            self.history = []
        self.history.append({"stage": stage, "data": data})
        return self


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


class BotSendText(BotSendBase):
    """Послать сообщение боту"""

    # fmt: off
    text: str | List[str | None] = Field(None, description="Текс сообщения или массив сообщений")  # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    format: str | None = Field(None, description="Формат сообщения (markdown (по умолчанию) и html по умолчанию)")  # noqa
    # fmt: on


class BotSendTextChannel(BotSendBase):
    """Послать сообщение боту"""

    # fmt: off
    text: str | List[str | None] = Field(None, description="Текс сообщения или массив сообщений")  # noqa
    plain: int | None = Field(None, description="Использовать моноширифный текст 1")  # noqa
    format: str | None = Field(None, description="Формат сообщения (markdown (по умолчанию) и html по умолчанию)")  # noqa
    # fmt: on


class BotSendPhoto(BotSendBase):
    """Послать рисунок боту"""

    # fmt: off
    photo: str = Field(..., description="Изображение")  # noqa
    caption: str | None = Field(None, description="Подпись изображения")  # noqa


class BotBaseTopic(HeaderEvent):
    """Базовое сообщение для бота"""

    chat_id: int

    def route_key(self):
        return f"{self.chat_id}"


class BotUpdateTopic(BotBaseTopic):
    """Создать новый топик, если нету или обновить текущий"""

    # fmt: off
    dialogues_id: int = Field(..., description="Идентификатор диалога")  # noqa
    caption: str = Field(..., description="Наименование топика")  # noqa
    emoji: str | None = Field(None, description="Emoji")  # noqa
    # fmt: on


class BotSendTextTopic(BotSendBase):
    """Послать сообщение в topic"""

    # fmt: off
    caption: str = Field(..., description="Наименование топика")  # noqa
    text: str | List[str | None] = Field(None, description="Текс сообщения")  # noqa
    dialogues_id: int = Field(..., description="Идентификатор диалога")  # noqa
    emoji: str | None = Field(None, description="Emoji")  # noqa
    # fmt: on


class BotEnteredReplyMessageTopic(BotEnteredClass):
    """Введен ответ на текст в topic"""

    # fmt: off
    reply_text: str | None = Field(..., description="На какой вопрос ответили")  # noqa
    dialogues_id: int = Field(..., description="Идентификтор диалога")  # noqa
    # fmt: on


class DialogueEnteredTextMessage(HeaderEvent):
    """Пришло входящее сообщение в диалог по клиенту"""

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента")  # noqa
    topic: str = Field(..., description="Наименование топика в диалоге")  # noqa
    text: str | List[str | None] = Field(None, description="Текс сообщения или массив сообщений")  # noqa
    # fmt: on


class DialogueCreateTopic(HeaderEvent):
    """Создать новый топик в диалоге, если не найден"""

    # fmt: off
    client_id: int = Field(..., description="Идентификатор клиента")  # noqa
    # fmt: on
