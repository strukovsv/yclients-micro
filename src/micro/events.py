import logging
import re

from types import FunctionType

logger = logging.getLogger(__name__)


def get_event_name(name: str) -> str:
    """Преобразовать имя события типа
    CamelCaseName в camel_case_name
    java.case.name в java_case_name
    snake_case_name в snake_case_name
    """
    # Преобразовать CamelCase
    _name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    # Преобразовать java.case
    return "_".join(_name.split("."))


class Events:

    @classmethod
    async def do(cls, js):
        event_name = js.get("event", None)
        if event_name:
            for name, func in cls.__dict__.items():
                if type(func) is FunctionType and (
                    get_event_name(event_name) + "_"
                ).startswith(f"{name}_"):
                    event_split = event_name.split(".")
                    # Кратко распечатать 200 символов json
                    js_example = {
                        key: value for key, value in js.items() if key != "event"
                    }
                    sjs = f"{js_example}"[0:200]
                    logger.info(
                        f'arrived message "{event_name}" to func: "{name}" : "{sjs}"'
                    )
                    await func(
                        [
                            event_split[i] if i < len(event_split) else ""
                            for i in range(0, 10)
                        ],
                        js,
                    )
