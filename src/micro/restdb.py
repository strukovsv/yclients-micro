import logging
import httpx

import jinja2

import config

logger = logging.getLogger(__name__)

sql = jinja2.Environment(loader=jinja2.FileSystemLoader("sql/"))


class RESTDB:

    async def rest_get(url: str, params: dict) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                r = await client.get(
                    f"{config.DATABASE_URL}{url}",
                    params=params,
                    timeout=10.0,
                )
                return r.json()
            except Exception as e:
                # Получить user token
                logger.error(f"{e=}")

    async def fetchall(query: str) -> dict:
        return await RESTDB.rest_get(
            "select",
            {
                "query": query,
            },
        )

    async def get_data(event_type: str, id: int):
        return await RESTDB.rest_get(
            "data",
            {
                "table": event_type,
                "id": id,
            },
        )


async def fetchall(template: str, **kwarg):
    sql_text = sql.get_template(template).render(**kwarg)
    logger.info(f"{sql_text}")
    return await RESTDB.fetchall(sql_text)


def get_classic_rows(rows: list) -> list:
    result = []
    if rows is not None and len(rows) > 0:
        # Добавить колонки
        row_cnt = 0
        for row in rows:
            row_cnt += 1
            if row_cnt == 1:
                result.append([field_name for field_name in row])
            result.append(
                [
                    field_values if field_values is not None else ""
                    for field_values in row.values()
                ]
            )
    return result


async def get_data(query: str, **kwarg):
    sql_text = sql.get_template(query).render(**kwarg)
    rows = await RESTDB.fetchall(sql_text)
    return get_classic_rows(rows)
