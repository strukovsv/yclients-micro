import inspect
import logging
import sys
import json

try:
    from schema_registry.client import AsyncSchemaRegistryClient, schema
except Exception:
    pass

from pydantic_avro.base import AvroBase

from micro.singleton import MetaSingleton

import micro.config as config

import micro.models.api_records
import micro.models.sync_events
import micro.models.system_events
import micro.models.bot_events
import micro.models.common_events
import micro.models.payment_events
import micro.models.timetable_events
import micro.models.client_events
import micro.models.cards_events
import micro.models.cron_events
import micro.models.buh_events
import micro.models.mail_events


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
                    # logger.info(f'{name} {obj} {type(obj)} {issubclass(obj, AvroBase)=}') # noqa
                    if (
                        issubclass(obj, AvroBase)
                        and name != "AvroBase"
                        and name != "HeaderEvent"
                    ):
                        result[name] = obj
            self._models = result
        return self._models

    def get_schema(self, schema_name: str, return_type: str = "json") -> dict:
        # Получить все классы из модуля
        for name, schema_obj in self.get_models().items():
            # Найти наш объект
            if schema_name.lower() == name.lower():
                # Вернуть avro схему
                if return_type == "avro":
                    return schema_obj.avro_schema(namespace="")
                else:
                    return schema_obj.schema()

    async def populate_schemes(self):
        if config.SCHEMA_REGISTRY_URL:
            async_client = AsyncSchemaRegistryClient(
                url=config.SCHEMA_REGISTRY_URL
            )
            schema_result = {"success": [], "incompatible": [], "error": []}
            # Перебрать все модули
            # Получить все классы из модуля
            for name, schema_obj in self.get_models().items():
                # logger.info(f"{name} : +{str(type(schema_obj))}+")
                if "<class 'pydantic.main.ModelMetaclass'>" == str(
                    type(schema_obj)
                ):
                    deployment_schema = schema_obj.avro_schema(
                        namespace="happiness"
                    )
                    # logger.info(f"{name} : {deployment_schema}")
                    avro_schema = schema.AvroSchema(deployment_schema)
                    try:
                        if await async_client.test_compatibility(
                            name, avro_schema
                        ):
                            schema_id = await async_client.register(
                                name, avro_schema
                            )
                            result = await async_client.check_version(
                                name, avro_schema
                            )
                            logger.info(f"{name} : {schema_id}")
                            schema_result["success"].append(
                                f"{name} : {result}"
                            )
                        else:
                            incompatible = (
                                await async_client.test_compatibility(
                                    subject=name,
                                    schema=avro_schema,
                                    verbose=True,
                                )
                            )
                            res = {
                                name: [mes for mes in incompatible["messages"]]
                            }
                            schema_result["incompatible"].append(res)
                    except Exception as e:
                        schema_result["error"].append(f"{name} : {e}")
            return schema_result
        else:
            raise Exception(
                "Не задана переменная окружения SCHEMA_REGISTRY_URL"
            )

    def get_asyncapi(self) -> dict:
        # http://localhost:8015/asyncapi
        # components:
        #   messages:
        #     sync.RecordUpdated:
        #       payload:
        #         schemaFormat: 'application/vnd.apache.avro;version=1.9.0'
        #         schema:
        #           $ref: 'http://localhost:8012/avro/RecordUpdated'
        event_list = {}
        for name, obj in self.get_models().items():
            description = obj.__doc__ if obj.__doc__ else ""
            # ", ".join(obj.__doc__.split("\n"))
            event_list[name] = {
                "description": description,
                "payload": {
                    "schema": {"$ref": f"http://localhost:8015/schemes/{name}"}
                },
            }
        result = {
            "asyncapi": "3.0.0",
            "info": {
                "title": "User Signup API",
                "version": "1.0.0",
                "description": "The API notifies you whenever a new user signs up in the application.",
            },
            "servers": {
                "kafkaServer": {
                    "host": "test.mykafkacluster.org:8092",
                    "description": "Kafka Server",
                    "protocol": "kafka",
                }
            },
            "components": {"messages": event_list},
        }
        return result

    def event_schemas(self) -> dict:
        new_schemes = {}
        for name, obj in self.get_models().items():
            new_schemes[name] = {
                "$ref": f"/schemes/{name}",
            }
        return new_schemes
