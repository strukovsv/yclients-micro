import logging

import jinja2

from jinja2 import Environment, DictLoader, FileSystemLoader, ChoiceLoader

from micro.utils import get_classic_rows
from micro.pg import DB
from micro.metrics import PG_UPDATES

logger = logging.getLogger(__name__)

constant_templates = {
    "YOGA_SERVICES": """
select
  s.id service_id,
  s.js->>'title' AS service_title
from services s
where s.js->>'title' ~* 'ЙОГА|СПИНА|ГАМАК|ИНДИВИДУАЛЬНОЕ ЗАНЯТИЕ'""",
    "YOGA": """
with
    yoga_services as (
        {% include 'YOGA_SERVICES' %}
)
SELECT
    r.id as record_id,
    to_date2(r.js ->> 'date'::text) AS record_dt,
    to_char(to_date2(r.js ->> 'date'::text), 'YYYY-MM') AS record_dt_month,
    to_char(to_date2(r.js ->> 'date'::text), 'YYYY-MM') AS record_dt_year,
    (r.js->'client'->>'id')::int AS client_id,
    s.service_id AS service_id,
    s.service_title AS service_title
FROM records r
JOIN yoga_services s ON s.service_id = (r.js->'services'->0->>'id')::int
WHERE (r.js->>'paid_full')::int = 1
    AND COALESCE(r.js->>'deleted', 'false') <> 'true'
""",
    "ACTIVE_CARDS": """
with active_cards as (
	select
	  (st1.js->'client'->>'id')::int as client_id,
	  (st1.js->>'cost')::float as costs,
	  c1.js js
	from cards c1
	join storage_transactions st1 on st1.id = (c1.js->>'goods_transaction_id')::int
	where (
	       (c1.js->'status'->>'title' = 'Активирован' and (c1.js->>'expiration_date')::date >= current_date)
	       or
		   (c1.js->'status'->>'title' = 'Выпущен' and (c1.js->>'created_date')::date > (current_date - 30))
		  )
)
select
  cl.id client_id,
  concat(
    case
      when length(cl.js->>'phone') = 12 then left(cl.js->>'phone', 5) || '•••' || right(cl.js->>'phone', 4)
      else cl.js->>'phone'
    end,
    ' ',
    cl.js->>'display_name'
  ) as "Клиент",
  concat(
    cl.js->>'phone',
    ' ',
    cl.js->>'display_name'
  ) as "Клиент, unmasked",
  string_agg(
    concat(
	  ac.js->>'number',
	  ' (',
	  ac.js->>'united_balance_services_count',
	  ':',
	  ac.js->'type'->>'united_balance_services_count',
	  '/',
	  concat(to_char((ac.js->>'created_date')::date, 'DD.MM.YY'),
	  '...',
	  to_char((ac.js->>'expiration_date')::date, 'DD.MM.YY')),
	  ')'),
	', ') "Активные абонементы",
  sum((ac.js->>'united_balance_services_count')::int) as "Занятий по абонементам, клв",
  min((ac.js->>'created_date')::date) as "Покупка абонементов, дата",
  to_char(min((ac.js->>'created_date')::date), 'YYYY-MM') as "Покупка абонементов, месяц",
  min((ac.js->>'activated_date')::date) as "Активация абонементов, дата",
  to_char(min((ac.js->>'activated_date')::date), 'YYYY-MM') as "Активация абонементов, месяц",
  max((ac.js->>'expiration_date')::date) as "Окончание абонементов, дата",
  to_char(max((ac.js->>'expiration_date')::date), 'YYYY-MM') as "Окончание абонементов, месяц",
  sum(ac.costs) as "Сумма продажи, руб",
  count(*) as "Активных абонементов, клв"
from active_cards ac join detail_clients cl on cl.id = ac.client_id
group by cl.id
"""
}


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
    for line in sql_text.split("\n"):
        logger.info(f'{line}')
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
