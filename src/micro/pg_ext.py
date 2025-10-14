import logging

import jinja2

from jinja2 import Environment, DictLoader, FileSystemLoader, ChoiceLoader

from micro.utils import get_classic_rows
from micro.pg import DB
from micro.metrics import PG_UPDATES
from micro.sql_templates import constant_templates

logger = logging.getLogger(__name__)


async def get_data(table_name, id: int = None, where: str = None):
    if id:
        for row in await DB().fetchall(
            f"select js from {table_name} where id = %(id)s", {"id": id}
        ):
            return row["js"]
    elif where:
        for row in await DB().fetchall(
            f"select js from {table_name} where {where}"
        ):
            return row["js"]
    else:
        return None


async def update(table_name: str, id: int, js: dict, func=None) -> str:
    result = await DB().update(table_name, id, js, func)
    PG_UPDATES.labels(result).inc()
    return result


async def select(template: str, **kwarg):
    template_path = kwarg.get("template_path", None)
    if template_path:
        loaders = [
            DictLoader(constant_templates),
            FileSystemLoader(template_path),
        ]
        sql_template = jinja2.Environment(loader=ChoiceLoader(loaders))
        sql_text = sql_template.get_template(template).render(**kwarg)
    else:
        loaders = [DictLoader(constant_templates), FileSystemLoader("sql/")]
        sql = jinja2.Environment(loader=ChoiceLoader(loaders))
        sql_text = sql.get_template(template).render(**kwarg)
    # for line in sql_text.split("\n"):
    #     logger.info(f"{line}")
    data = await DB().fetchall(sql_text, kwarg.get("params", {}))
    # Перечислить список выводимых колонок
    columns = kwarg.get("columns", None)
    if columns:
        result = []
        for row in data:
            result.append(
                {column: row[column] for column in columns if column in row}
            )
        data = result
    if kwarg.get("as_classic_rows", None):
        return get_classic_rows(data)
    else:
        return data


async def execute(query, params=None):
    return await DB().execute(query, params)


async def fetchall(query, params=None):
    return await DB().fetchall(query, params)


async def fetchone(query, params=None):
    return await DB().fetchone(query, params)


async def returning(query, params=None):
    return await DB().returning(query, params)
