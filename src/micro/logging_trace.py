# Подключить логирование главного модуля
import logging
import uuid

from micro.singleton import MetaSingleton

logger = logging.getLogger(__name__)


class TRACE(metaclass=MetaSingleton):

    trace_id: str

    def __init__(self):
        # self.trace_id: str = "start"
        self.new()

    def set(self, trace_id: str):
        self.trace_id = trace_id
        return self.trace_id

    def new(self):
        new_uuid = uuid.uuid4().hex[:12]
        # logger.info(f"new:{new_uuid}", stack_info=True)
        return self.set(new_uuid)


old_factory = logging.getLogRecordFactory()


def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.name = TRACE().trace_id
    return record


logging.setLogRecordFactory(record_factory)
