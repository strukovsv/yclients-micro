import logging
import psycopg_pool
from psycopg.rows import dict_row

from micro.singleton import MetaSingleton

import micro.config as config
from micro.metrics import PG_EXECUTE_CNT, PG_FETCHALL_CNT, PG_UPDATES

logger = logging.getLogger(__name__)


class DB(metaclass=MetaSingleton):

    pool = None

    def __init__(self):
        logger.info("init db")

    def postgres_conninfo(self):
        conn = {
            "dbname": config.PG_DATABASE,
            "host": config.PG_HOST,
            "user": config.PG_USER,
            "password": config.PG_PASSWORD,
            "port": config.PG_PORT,
        }
        return " ".join([f"{key}={value}" for key, value in conn.items()])

    async def open_pool(self):
        if not self.pool:
            # Подключить pool соединений с Postgres
            self.pool = psycopg_pool.AsyncConnectionPool(
                conninfo=self.postgres_conninfo(),
                open=False,
                min_size=1,
                max_size=2,
                kwargs={"autocommit": True, "row_factory": dict_row},
            )
            await self.pool.open()
            await self.pool.wait()
            logger.info("open pool db")

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("close pool db")

    async def execute(self, query, params=None):
        await self.open_pool()
        async with self.pool.connection() as conn:
            if isinstance(query, list):
                async with conn.transaction():
                    async with conn.cursor() as acur:
                        for item in query:
                            PG_EXECUTE_CNT.inc()
                            await acur.execute(
                                item["sql"], item.get("params", {})
                            )
                        return None
            else:
                async with conn.cursor() as acur:
                    PG_EXECUTE_CNT.inc()
                    await acur.execute(query, params)
                    return acur.rowcount

    async def returning(self, query, params=None):
        await self.open_pool()
        async with self.pool.connection() as conn:
            if isinstance(query, list):
                raise
            else:
                async with conn.cursor() as acur:
                    PG_EXECUTE_CNT.inc()
                    await acur.execute(query, params)
                    return await acur.fetchone()

    async def fetchall(self, query, params=None):
        await self.open_pool()
        async with self.pool.connection() as conn:
            async with conn.cursor() as acur:
                try:
                    await acur.execute(query, params)
                except Exception as e:
                    logger.error(f'{e}: {query=} {params=}')
                    raise
                PG_FETCHALL_CNT.inc()
                return await acur.fetchall()

    async def fetchone(self, query, params=None):
        await self.open_pool()
        for row in await self.fetchall(query, params):
            return row
        return None
