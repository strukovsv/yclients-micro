import asyncio
import os
import logging
import json
import datetime
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from starlette_exporter import PrometheusMiddleware, handle_metrics
from contextlib import asynccontextmanager

import sentry_sdk

from micro.utils import hide_passwords
import micro.config as config
from micro.kafka_consumer import KafkaConsumer, capture
from micro.kafka_producer import KafkaProducer
from micro.status import Status
from micro.schemes import Schema
from micro.models.common_events import ServiceStarted

logger = logging.getLogger(__name__)

app = None

sentry_sdk.init(
    server_name=os.environ.get("SENTRY_SERVER", None),
    max_breadcrumbs=10,
)


class BackgroundRunner:

    async def run_main(self, app):

        async def cycle():
            try:
                while True:
                    # Получить пакет сообщений из kafka
                    result = await KafkaConsumer().get_messages()
                    # Перебрать пакеты
                    for tp, messages in result.items():
                        # Если есть сообщение
                        if messages:
                            for message in messages:
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
            except Exception:
                traceback.print_exc()
                raise

        while True:
            if await Status().error():
                logger.info(
                    f"service works with errors :( sleep {config.SLEEP_AFTER_ERROR_SECOND}"  # noqa
                )
                # await asyncio.sleep(config.SLEEP_AFTER_ERROR_SECOND)
                await asyncio.sleep(15)
                # Попробовать еще раз
                await Status().set_ok()
            else:
                try:
                    # Подключиться к kafka
                    # logger.info('start kafka producer')
                    # await KafkaProducer().start()
                    # После запуска kafka запустить сервис
                    async_task = asyncio.create_task(cycle())
                    if hasattr(app, "runner"):
                        asyncio.create_task(app.runner())
                    # Событие запуска сервиса
                    await ServiceStarted(
                        service_name=app.summary,
                        date=(datetime.now().strftime("%d.%m.%Y %H:%M:%S")),
                    ).send(key=app.summary)
                    # await KafkaProducer().send_event(
                    #     event=f"service.start.{app.summary}",
                    #     key=app.summary,
                    #     message={},
                    # )
                    await async_task
                except Exception:
                    traceback.print_exc()
                    # raise
                    # logger.info(f"exception: {e}")
                finally:
                    logger.info("Closed service")
                    # Отключиться от kafka
                    # await yclient.close()
                    logger.info("stop kafka producer")
                    await KafkaProducer().stop()
                    logger.info("stop kafka consumer")
                    await KafkaConsumer().stop()

                    if hasattr(app, "del_objects"):
                        dels = asyncio.create_task(app.del_objects())
                        await dels

                    # Закрыть kafka
                    await Status().set_error()
                    # await asyncio.sleep(
                    #     app.runner_period_secs
                    #     if hasattr(app, "runner_period_secs")
                    #     else 120
                    # )


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


@app.get("/health")
async def healthcheck():
    if hasattr(app, "healthcheck"):
        return_value = await app.healthcheck()
        if return_value:
            return return_value
        else:
            return JSONResponse(
                content={"message": "Service works with errors"},
                status_code=500,
            )
    else:
        if await Status().ok():
            return {"status": "UP"}
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


@app.get("/schemes/{schema_name}")
async def get_schemes(schema_name: str):
    return JSONResponse(
        content=Schema().get_schema(
            schema_name=schema_name, return_type="json"
        ),
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/avro/{schema_name}")
async def get_avro(schema_name: str):
    return JSONResponse(
        content=Schema().get_schema(
            schema_name=schema_name, return_type="avro"
        ),
        headers={"Access-Control-Allow-Origin": "*"},
    )


@app.get("/populate_schemes")
async def populate_schemes():
    return await Schema().populate_schemes()


@app.get("/asyncapi")
async def asyncapi():
    return JSONResponse(
        content=Schema().get_asyncapi(),
        headers={"Access-Control-Allow-Origin": "*"},
    )


def custom_openapi():
    openapi_schema = get_openapi(
        title="FastAPI",
        version="1.0.0",
        description="This is a custom OpenAPI schema",
        routes=app.routes,
    )
    for scheme_name, scheme_dict in (Schema().event_schemas()).items():
        openapi_schema["components"]["schemas"][scheme_name] = scheme_dict
    return openapi_schema


app.openapi = custom_openapi


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
