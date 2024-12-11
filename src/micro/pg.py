import logging
import json
import hashlib
import psycopg_pool
from psycopg.rows import dict_row
import jinja2

from .utils import get_classic_rows

import config
from .metrics import PG_EXECUTE_CNT, PG_FETCHALL_CNT, PG_UPDATES

logger = logging.getLogger(__name__)


sql = jinja2.Environment(loader=jinja2.FileSystemLoader("sql/"))


class DB:

    pool = None

    def __init__(self, pool):
        self.pool = pool

    @classmethod
    def postgres_conninfo(cls):
        conn = {
            "dbname": config.PG_DATABASE,
            "host": config.PG_HOST,
            "user": config.PG_USER,
            "password": config.PG_PASSWORD,
            "port": config.PG_PORT,
        }
        return " ".join([f"{key}={value}" for key, value in conn.items()])

    @classmethod
    async def create(cls):
        # Подключить pool соединений с Postgres
        pool = psycopg_pool.AsyncConnectionPool(
            conninfo=cls.postgres_conninfo(),
            open=False,
            min_size=1,
            max_size=2,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        await pool.open()
        await pool.wait()
        return cls(pool)

    async def execute(self, query, params=None):
        async with self.pool.connection() as conn:
            async with conn.cursor() as acur:
                PG_EXECUTE_CNT.inc()
                await acur.execute(query, params)

    async def fetchall(self, query, params=None):
        async with self.pool.connection() as conn:
            async with conn.cursor() as acur:
                await acur.execute(query, params)
                PG_FETCHALL_CNT.inc()
                return await acur.fetchall()

    async def fetchone(self, query, params=None):
        for row in await self.fetchall(query, params):
            return row
        return None

    async def update(
        self, table_name: str, id: int, js: dict, func=None
    ) -> str:
        """Положить json в базу данных

        table_name -- имя таблицы
        id -- идентификатор таблицы
        js -- входной json, если None - то удалить строку из базы данных
        func -- вызываемая функция при событии изменения базы данных
        """
        # Положить сообщение в базу и отправить в kafka
        params = {
            "id": id,
            "js": json.dumps(js, ensure_ascii=False),
        }
        params["hash"] = hashlib.sha1(params["js"].encode()).hexdigest()
        # Прочитать текущее состояние таблицы
        current = await self.fetchone(
            query=f"""
select js, coalesce(hash,'~') hash
from {table_name}
where id = %(id)s""",
            params={"id": id},
        )
        if current:
            # Запись найдена в базе данных
            if js is None:
                # Удалить запись из базы данных
                await self.execute(
                    query=f"delete from {table_name} where id = %(id)s",
                    params={"id": id},
                )
                if func:
                    await func(
                        table_name=table_name,
                        operation="delete",
                        id=id,
                        new_js=None,
                        old_js=current["js"],
                    )
                return "delete"
            else:
                # Запись найдена в базе данных
                if current["hash"] != params["hash"]:
                    # update, hash не соответствует
                    # Обновить базу данных
                    await self.execute(
                        f"""
    update {table_name}
    set js = %(js)s, hash = %(hash)s
    where id = %(id)s""",
                        params,
                    )
                    if func:
                        await func(
                            table_name=table_name,
                            operation="update",
                            id=id,
                            new_js=js,
                            old_js=current["js"],
                        )
                    return "update"
                else:
                    return None
        else:
            # insert, запись не найдена в базе данных
            await self.execute(
                f"""
insert into {table_name} (id, js, hash)
values (%(id)s, %(js)s, %(hash)s)""",
                params,
            )
            if func:
                await func(
                    table_name=table_name,
                    operation="insert",
                    id=id,
                    new_js=js,
                )
            return "insert"


postgres: DB = None


async def get_db() -> DB:
    """Подключиться к базе данных postgres"""
    global postgres
    postgres = postgres if postgres else await DB.create()
    return postgres


async def execute(query, params=None):
    await (await get_db()).execute(query, params)


async def fetchall(query, params=None):
    return await (await get_db()).fetchall(query, params)


async def fetchone(query, params=None):
    return await (await get_db()).fetchone(query, params)


async def get_data(table_name, id: int = None, where: str = None):
    if id:
        for row in await (await get_db()).fetchall(
            f"select js from {table_name} where id = %(id)s", {"id": id}
        ):
            return row["js"]
    elif where:
        for row in await (await get_db()).fetchall(
            f"select js from {table_name} where {where}"
        ):
            return row["js"]
    else:
        return None


async def update(table_name: str, id: int, js: dict, func=None) -> str:
    result = await (await get_db()).update(table_name, id, js, func)
    PG_UPDATES.labels(result).inc()
    return result


async def select(template: str, **kwarg):
    template_path = kwarg.get("template_path", None)
    if template_path:
        logger.info(f'{template_path=} {template=}')
        sql_template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path)
        )
        sql_text = sql_template.get_template(template).render(**kwarg)
    else:
        sql_text = sql.get_template(template).render(**kwarg)
    data = await fetchall(sql_text)
    # logger.info(f'{template=} {data=} {sql_text=}')
    if kwarg.get("as_classic_rows", None):
        return get_classic_rows(data)
    else:
        return data
