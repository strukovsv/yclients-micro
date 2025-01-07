# Подключить логирование главного модуля
import logging
import pytest

from micro.singleton import MetaSingleton

logger = logging.getLogger(__name__)


class Test(metaclass=MetaSingleton):

    def __init__(self, a):
        self.a = a
        logger.info(f"init {self=} {a=}")

    async def aio_test(self, a):
        logger.info(f"init {a=}")


# def test1():
#     test = Test(10)
#     logger.info(f"{test=} {test.a=}")
#     test = Test(20)
#     logger.info(f"{test=} {test.a=}")


@pytest.mark.asyncio
async def test2():
    await Test(10).aio_test(10)
    await Test(20).aio_test(20)
