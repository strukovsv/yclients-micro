"""
zilogLib library v.0.0.0
The MIT License Copyright 2023 sstrukov
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette_exporter import PrometheusMiddleware, handle_metrics
from contextlib import asynccontextmanager
import traceback
import asyncio
import os
import logging

import sentry_sdk

from .utils import hide_passwords

log = logging.getLogger()

app = None

sentry_sdk.init(
    server_name=os.environ.get("SENTRY_SERVER", None),
    max_breadcrumbs=10,
)


class BackgroundRunner:

    async def run_main(self, app):
        while True:
            if hasattr(app, "runner"):
                try:
                    await app.runner()
                except Exception:
                    log.error("run_main : {}".format(traceback.format_exc()))
            await asyncio.sleep(
                app.runner_period_secs
                if hasattr(app, "runner_period_secs")
                else 120
            )


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
        return True


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
