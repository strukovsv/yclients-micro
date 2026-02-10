import asyncio
import os
import logging
import json
import datetime
import traceback
import time
import threading

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette_exporter import PrometheusMiddleware, handle_metrics
from contextlib import asynccontextmanager

import sentry_sdk

from micro.utils import hide_passwords
import micro.config as config
from micro.kafka_consumer import KafkaConsumer, capture
from micro.kafka_producer import KafkaProducer
from micro.status import Status
from micro.schemes import Schema
from micro.models.common_events import ServiceStarted, InfoEvent, Live
from micro.telegram import send_start_service

from micro.kafka_consumer import event_handler

logger = logging.getLogger(__name__)

app = None

sentry_sdk.init(
    server_name=os.environ.get("SENTRY_SERVER", None),
    max_breadcrumbs=10,
    default_integrations=False,
)


class BackgroundRunner:

    async def run_main(self, app):

        async def cycle():
            try:
                while True:
                    if config.SRC_TOPIC:
                        # Получить пакет сообщений из kafka
                        result = await KafkaConsumer().get_messages()
                        # Перебрать пакеты
                        for tp, messages in result.items():
                            # Если есть сообщение
                            if messages:
                                for message in messages:
                                    # logger.info(f'{message=}')
                                    # Добавить в сообщение время создания
                                    message_dict = json.loads(message.value)
                                    message_dict["create_event_timestamp"] = (
                                        datetime.datetime.fromtimestamp(
                                            message.timestamp / 1000
                                        ).strftime("%d.%m.%Y %H:%M:%S")
                                    )
                                    # Обработать сообщение
                                    # legasy
                                    if app.events:
                                        await app.events.do(message_dict)
                                    # new
                                    await capture(message_dict)

                                await KafkaConsumer().partition_commit(
                                    tp, messages[-1].offset + 1
                                )
                    else:
                        await asyncio.sleep(60)
            except Exception:
                traceback.print_exc()
                raise

        while True:
            if await Status().error():
                logger.info(
                    f"service works with errors :( sleep {config.SLEEP_AFTER_ERROR_SECOND}"  # noqa
                )
                await asyncio.sleep(config.SLEEP_AFTER_ERROR_SECOND)
                # Попробовать еще раз
                await Status().set_ok()
            else:
                try:
                    # Подключиться к kafka
                    # logger.info('start kafka producer')
                    # await KafkaProducer().start()
                    # После запуска kafka запустить сервис
                    async with asyncio.TaskGroup() as tg:
                        # Запустить обработку
                        logger.info("start task cycle")
                        tg.create_task(cycle(), name="cycle")
                        if hasattr(app, "runner"):
                            logger.info("start task runner")
                            tg.create_task(app.runner(), name="runner")
                        # Событие запуска сервиса
                        # Отправим независимо от жизни других сервисов,
                        # непосредственно в телеграмм
                        await send_start_service(service_name=app.summary)
                except BaseException:
                    logger.error(traceback.format_exc())
                finally:
                    logger.info("start close service")
                    # Отключиться от kafka
                    logger.info("stop kafka producer")
                    await KafkaProducer().stop()
                    logger.info("stop kafka consumer")
                    await KafkaConsumer().stop()

                    if hasattr(app, "del_objects"):
                        logger.info("del_objects")
                        dels = asyncio.create_task(app.del_objects())
                        await dels

                    await Status().set_error()
                    logger.info("stop service")


runner = BackgroundRunner()


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(runner.run_main(app))
    yield


app = FastAPI(
    title="fastapi",
    lifespan=lifespan,
    openapi_url="/openapi.json" if os.environ.get("OPENAPI", None) else "",
)

app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

app.events = None


@app.get("/threading")
async def get_threading():
    return {"pid": os.getpid(), "thread": threading.get_ident()}

@app.get("/envs")
async def get_environments():
    """
    Получить параметры вызова микросервиса
    """
    envs = dict(os.environ.items())
    envs_sorted = {}
    for key in sorted(envs.keys()):
        envs_sorted[key] = envs[key]
    return hide_passwords(envs_sorted)


# Глобальная переменная с моментом старта приложения
_app_start_time = time.time()


def uptime_str() -> str:
    uptime_seconds = int(time.time() - _app_start_time)

    days, remainder = divmod(uptime_seconds, 86400)
    hours, seconds = divmod(remainder, 3600)

    return f"{days}d {hours}h {seconds}s"


@app.get("/health")
async def healthcheck():
    if hasattr(app, "healthcheck"):
        return_value = await app.healthcheck()
        if return_value:
            if isinstance(return_value, dict):
                return {**return_value, "uptime": uptime_str()}
            else:
                return return_value
        else:
            return JSONResponse(
                content={"message": "Service works with errors"},
                status_code=500,
            )
    else:
        if await Status().ok():
            return {"status": "UP", "uptime": uptime_str()}
        else:
            return JSONResponse(
                content={"message": "Service works with errors"},
                status_code=500,
            )


@app.get("/ui/changelog", response_class=HTMLResponse)
@app.get("/changelog")
async def get_changelog(request: Request):
    """
    Описание изменений сервиса по датам
    """
    changelog = app.changelog if hasattr(app, "changelog") else "changelog.md"
    service_name = (
        f"{app.service_name}: " if hasattr(app, "service_name") else ""
    )
    if os.path.isfile(changelog):
        with open(changelog) as f:
            lines = [line.replace("\n", "") for line in f.readlines()]
    else:
        lines = [f"{changelog} not exist"]
    lines_br = "<br/>".join(lines)
    if "text/html" in request.headers.get("accept", None):
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>{service_name}{changelog}</title>
        </head>
        <body>
            <div>
                {lines_br}
            </div>
            <br/>
            <br/>
        </body>
        </html>"""
    else:
        return lines


# Do not log metrics and healthcheck
class EndpointFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        excluded_endpoints = ["GET /metrics", "GET /health"]
        output = True
        logged_msg = record.getMessage()
        for endpoint in excluded_endpoints:
            if logged_msg.find(endpoint) > -1:
                output = False
        return output


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())


@event_handler("Live")
async def live_event(obj: Live):
    """Сообщение live"""
    date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    await InfoEvent(text=f"😊 {date} : service {app.summary} is live !").send()
