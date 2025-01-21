import inspect
import logging
import sys
import json

try:
    from schema_registry.client import AsyncSchemaRegistryClient, schema
except Exception:
    pass

from pydantic_avro.base import AvroBase

import micro.models.api_records
import micro.models.sync_events
import micro.models.system_events
import micro.models.bot_events
import micro.models.worker_events


logger = logging.getLogger(__name__)


def get_models():
    modules = [
        module_object
        for module_name, module_object in sys.modules.items()
        if module_name.startswith("micro.models.")
    ]
    result = []
    for module_object in modules:
        for name, obj in inspect.getmembers(module_object, inspect.isclass):
            result.append((name, obj))
    return result


def get_schema(schema_name: str, return_type: str = "json") -> dict:
    # Получить все классы из модуля
    for name, schema_obj in get_models():
        # Найти наш объект
        if schema_name.lower() == name.lower():
            # Вернуть avro схему
            if return_type == "avro":
                return schema_obj.avro_schema(namespace="")
            else:
                return schema_obj.schema()


async def populate_schemes():
    async_client = AsyncSchemaRegistryClient(url="http://192.168.1.143:8081")
    schema_result = {"success": [], "incompatible": [], "error": []}
    # Перебрать все модули
    # Получить все классы из модуля
    for name, schema_obj in get_models():
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
