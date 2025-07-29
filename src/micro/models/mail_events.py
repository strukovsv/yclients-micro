from __future__ import annotations
import logging
from typing import Any, List, Optional, Union
from datetime import datetime
from pydantic import Field
import re

from micro.models.header_event import HeaderEvent

logger = logging.getLogger(__name__)

# fmt: off


class MailMessage(HeaderEvent):
    """Пришло письмо по почте
    """
    uid: str = Field(..., description="Уникальный идентификатор сообщений в почте") # noqa
    body: str = Field(..., description="Тело сообщения") # noqa
    plain: str = Field(..., description="Тело сообщения как plain") # noqa
    date: str = Field(..., description="Дата сообщения Tue, 22 Jul 2025 16:03:46 +0700") # noqa
    content_type: str = Field(..., description="Формат сообщения (html...)") # noqa
    subject: str = Field(..., description="Заголовок сообщения") # noqa
    sender: str = Field(..., description="Отправитель сообщения (расшифровка)") # noqa
    sender_email: str = Field(..., description="Отправитель сообщения (адрес)") # noqa

    def print(self):
        """Распечатать plain тело письма построчно
        """
        for line in self.plain.split("\n"):
            logger.info(f"{line}")

    def in_subject(self, substr: str) -> bool:
        """Проверяет вхождение строки в subject письма,
        не regex !!!

        :param str substr: вхождение
        :return bool: входит подстрока
        """
        return substr.lower() in self.subject.lower()

    def text(self) -> str:
        """Получить plain тело как одна строка.
        Перевод, заменяется на space
        """
        return " ".join(self.plain.split("\n"))

    def find(self, pattern: str) -> str:
        """Mining данных из plain тела сообщения

        :param str pattern: regex паттерн поиска,
        :return str: возвращаем первую группу (), не найдено, то None
        """
        match = re.match(pattern, self.text())
        if match:
            return match.group(1)
        else:
            return None

    def render(self, text: str) -> str:
        for pattern in re.findall(r"\^.+\$", text):
            logger.info(f'{pattern}')
            resultStr = str(self.find(pattern))
            text = text.replace(pattern, resultStr)
        return text
