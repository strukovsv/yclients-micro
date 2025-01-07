# Подключить логирование главного модуля
import logging
import dictdiffer

logger = logging.getLogger(__name__)


def test1():
    message = {}
    message["old"] = {"a": 10}
    message["data"] = {"a": 20}
    result = list(dictdiffer.diff(message["old"], message["data"]))
    patched = dictdiffer.patch(result, message["old"])
    logger.info(f"{result=}")
