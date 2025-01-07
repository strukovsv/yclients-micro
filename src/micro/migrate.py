# Системные библиотеки
import logging
import os

import yoyo

logger = logging.getLogger(__name__)

import .config

async def execute(_config):
    """
    Запустить миграцию БД
    """
    mirgate_path = os.getcwd() + "/migrations"
    # Получить данные подключения
    database = config.PG_DATABASE
    host = config.PG_HOST
    user = config.PG_MIGRATE_USER
    password = config.PG_MIGRATE_PASSWORD
    port = config.PG_MIGRATE_PORT
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
