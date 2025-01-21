import logging

from micro.singleton import MetaSingleton


logger = logging.getLogger(__name__)


class Status(metaclass=MetaSingleton):

    __error__: bool = False
    __message__: str = None

    async def ok(self):
        return not self.__error__

    async def error(self):
        return self.__error__

    async def set_ok(self):
        self.__error__ = False

    async def set_error(self):
        self.__error__ = True

    async def get_message(self):
        return self.__message__

    async def set_message(self, message):
        self.__message__ = message