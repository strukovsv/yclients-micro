import logging
import inspect
import sys

from micro.singleton import MetaSingleton
from pydantic import BaseModel

import micro.models.system_events  # noqa
import micro.models.bot_events  # noqa
import micro.models.common_events  # noqa
import micro.models.payment_events  # noqa
import micro.models.timetable_events  # noqa
import micro.models.client_events  # noqa
import micro.models.cards_events  # noqa
import micro.models.cron_events  # noqa
import micro.models.mail_events  # noqa
import micro.models.chat_events  # noqa
import micro.models.crm_events  # noqa


logger = logging.getLogger(__name__)


class Schema(metaclass=MetaSingleton):

    _models: list = None

    def __init__(self):
        pass

    def get_models(self):
        """Получить список объектов и закэшировать"""
        if not self._models:
            modules = [
                module_object
                for module_name, module_object in sys.modules.items()
                if module_name.startswith("micro.models.")
            ]
            result = {}
            for module_object in modules:
                for name, obj in inspect.getmembers(
                    module_object, inspect.isclass
                ):
                    if issubclass(obj, BaseModel) and name != "HeaderEvent":
                        result[name] = obj
            self._models = result
        return self._models
