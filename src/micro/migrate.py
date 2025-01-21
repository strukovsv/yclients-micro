# Системные библиотеки
import logging
import os

import yoyo

from micro.utils import getenv

logger = logging.getLogger(__name__)


async def execute():
    """
    Запустить миграцию БД
    """
    mirgate_path = os.getcwd() + "/migrations"
    # Получить данные подключения
    database = getenv("DB_PG_BASE", None)
    host = getenv("DB_PG_HOST", None)
    user = getenv("DB_PG_USR_OWNER", None)
    password = getenv("DB_PG_PWD_OWNER", None)
    port = getenv("DB_PG_PORT_MIGRATION", None)
    url = (
        f"postgresql+psycopg://{user}:{password}@{host}/{database}?port={port}"
    )
    url_print = (
        f"postgresql+psycopg://{user}:***@{host}/{database}?port={port}"
    )
    logging.info(
        f'start migrate yoyo, for postgres "{url_print}". Path migrate files "{mirgate_path}"'  # noqa
    )
    backend = yoyo.get_backend(url)
    # Директорий миграций
    migrations = yoyo.read_migrations(mirgate_path)
    # Выполнить миграции
    with backend.lock():
        # Apply any outstanding migrations
        backend.apply_migrations(backend.to_apply(migrations))
