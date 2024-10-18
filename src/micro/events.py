import logging

from types import FunctionType

from .metrics import DO_EVENTS_CNT, WORKED_EVENTS_CNT

logger = logging.getLogger(__name__)


class Events:

    @classmethod
    async def do(cls, js):
        DO_EVENTS_CNT.inc()
        for name, func in cls.__dict__.items():
            if type(func) is FunctionType and (
                ("_".join(js["event"].split("."))) + "_"
            ).startswith(f"{name}_"):
                WORKED_EVENTS_CNT.inc()
                event_split = js["event"].split(".")
                logger.info(f'event: {js["event"]} => {name}')
                await func(
                    [
                        event_split[i] if i < len(event_split) else ""
                        for i in range(0, 10)
                    ],
                    js,
                )
