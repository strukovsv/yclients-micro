import logging
import json
import hashlib
import dictdiffer
import psycopg_pool
from psycopg.rows import dict_row

try:
    import jinja2
except Exception:
    pass

from micro.utils import get_classic_rows
from micro.singleton import MetaSingleton
from micro.kafka_producer import KafkaProducer

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
            async with conn.cursor() as acur:
                PG_EXECUTE_CNT.inc()
                await acur.execute(query, params)

    async def fetchall(self, query, params=None):
        await self.open_pool()
        async with self.pool.connection() as conn:
            async with conn.cursor() as acur:
                await acur.execute(query, params)
                PG_FETCHALL_CNT.inc()
                return await acur.fetchall()

    async def fetchone(self, query, params=None):
        await self.open_pool()
        for row in await self.fetchall(query, params):
            return row
        return None

    async def send_message(self, event, message):
        ftable = message["event"]
        message["event"] = ftable + "." + event
        logger.info(
            f'send: {message["event"]} : {message["id"]}'  # noqa
        )  # noqa
        message["message_id"] = f'{ftable}:{message["id"]}'
        await KafkaProducer().send_event(message, message["event"])

    async def delete(self, tname, id, row):
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as acur:
                    # Скопировать текущую запись из базы как есть
                    await acur.execute(
                        f"""
insert into arch_{tname} (id, js, hash, operation, moment)
select id, js, hash, operation, moment
from {tname}
where id = {id}"""
                    )
                    # Добавить эту же запись с флагом удаления
                    await acur.execute(
                        f"""
insert into arch_{tname} (id, js, hash, operation, moment)
select id, js, hash, 'D' as operation, current_timestamp as moment
from {tname}
where id = {id}"""
                    )
                    # Удалить запись в базе
                    await acur.execute(f"delete from {tname} where id = {id}")
                    await self.send_message(
                        "delete",
                        {"event": f"db.{tname}", "id": id, "data": row},
                    )

    async def ins(self, tname, params, message):
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as acur:
                    # Добавить новую строку в базу
                    await acur.execute(
                        f"""
insert into {tname} (id, js, hash, operation, moment)
values (%(id)s, %(js)s, %(hash)s, 'I', current_timestamp)""",
                        params,
                    )
                    await self.send_message("insert", message)

    async def upd(self, tname, params, message):
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as acur:
                    # Перенсти старое значение в базу как есть
                    await acur.execute(
                        f"""
insert into arch_{tname} (id, js, hash, operation, moment)
select id, js, hash, operation, moment
from {tname}
where id = %(id)s""",
                        params,
                    )
                    # Обновить запись в базе. Пометить, что она обновлена
                    # и зафиксировать это время
                    await acur.execute(
                        f"""
update {tname}
set js = %(js)s, hash = %(hash)s, operation = 'U', moment = current_timestamp
where id = %(id)s""",
                        params,
                    )
                    diff = list(
                        dictdiffer.diff(message["old"], message["data"])
                    )
                    logger.info(f"{diff=}")
                    message["diff"] = diff
                    await self.send_message("update", message)

    async def insert(self, message, ftable):
        # Положить сообщение в базу и отправить в kafka
        params = {
            "id": message["id"],
            "js": json.dumps(message["data"], ensure_ascii=False),
        }
        # Вычислить hash значение json
        params["hash"] = hashlib.sha1(params["js"].encode()).hexdigest()
        # Прочитать текущее состояние данных
        current = await self.fetchall(
            query=f"""
select js, coalesce(hash,'~') hash
from {ftable}
where id = %(id)s""",
            params={"id": message["id"]},
        )
        if current:
            # Если есть строка данных, сверим hash
            if current[0]["hash"] != params["hash"]:
                # hash не сошелся, то обновим базу данных
                # положим в сообщение старое значение данных
                message["old"] = current[0]["js"]
                # Обновим строку данных
                await self.upd(
                    # Наименование таблицы
                    tname=ftable,
                    # Параметры
                    params=params,
                    # Сообщение отправки в kafka
                    message=message,
                )
                # Вернуть, что запись обновлена
                return "update"
        else:
            # иначе добавить запись
            await self.ins(
                # Наименование таблицы
                tname=ftable,
                # Параметры
                params=params,
                # Сообщение отправки в kafka
                message=message,
            )
            # Вернуть, что запись добавлена
            return "insert"
        return None

    async def get_data(self, table_name, id: int = None, where: str = None):
        if id:
            for row in await self.fetchall(
                f"select js from {table_name} where id = %(id)s", {"id": id}
            ):
                return row["js"]
        elif where:
            for row in await self.fetchall(
                f"select js from {table_name} where {where}"
            ):
                return row["js"]
        else:
            return None

    async def update(
        self, table_name: str, id: int, js: dict, func=None
    ) -> str:
        result = await self.update(table_name, id, js, func)
        PG_UPDATES.labels(result).inc()
        return result

    async def select(self, template: str, **kwarg):
        template_path = kwarg.get("template_path", None)
        if template_path:
            logger.info(f"{template_path=} {template=}")
            sql_template = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_path)
            )
            sql_text = sql_template.get_template(template).render(**kwarg)
        else:
            sql = jinja2.Environment(loader=jinja2.FileSystemLoader("sql/"))
            sql_text = sql.get_template(template).render(**kwarg)
        data = await self.fetchall(sql_text)
        if kwarg.get("as_classic_rows", None):
            return get_classic_rows(data)
        else:
            return data
