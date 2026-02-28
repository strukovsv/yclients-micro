import logging

from micro.singleton import MetaSingleton

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

    def get_schema(self, schema_name: str, return_type: str = "json") -> dict:
        # Получить все классы из модуля
        for name, schema_obj in self.get_models().items():
            # Найти наш объект
            if schema_name.lower() == name.lower():
                return schema_obj.schema()

    def event_schemas(self) -> dict:
        new_schemes = {}
        for name, obj in self.get_models().items():
            new_schemes[name] = {
                "$ref": f"/schemes/{name}",
            }
        return new_schemes
