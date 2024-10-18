# Подключить логирование главного модуля
import logging

logger = logging.getLogger(__name__)

# Подключить библиотеку fastapi
import micro.service

app = micro.service.app

app.service_name = "test service"

# Подключить обработку
import tests.tasks as tasks

app.runner_period_secs = 10
app.runner = tasks.task


# Подключить обработку здоровья
async def health():
    return False


app.healthcheck = health

# Установить api docs
app.title = "Service title"
app.version = "1.0.1"
app.summary = "summary"
app.description = "description"

# Подключить обработчики
import tests.ui as ui

app.include_router(ui.api_router)
app.include_router(ui.user_router)
