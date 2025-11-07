constant_templates = {

    "template_yoga_services.sql": """
select
  s.id service_id,
  s.js->>'title' AS service_title
from services s
where s.js->>'title' ~* 'ЙОГА|СПИНА|ГАМАК|ИНДИВИДУАЛЬНОЕ ЗАНЯТИЕ'""",

    "template_yoga.sql": """
with
    yoga_services as (
        {% include 'template_yoga_services.sql' %}
)
SELECT
    r.id as record_id,
    to_date2(r.js ->> 'date'::text) AS record_dt,
    to_date2month(r.js ->> 'date'::text) AS record_dt_month,
    to_date2year(r.js ->> 'date'::text) AS record_dt_year,
    (r.js->'client'->>'id')::int AS client_id,
    s.service_id AS service_id,
    s.service_title AS service_title
FROM records r
JOIN yoga_services s ON s.service_id = (r.js->'services'->0->>'id')::int
WHERE (r.js->>'paid_full')::int = 1
    AND COALESCE(r.js->>'deleted', 'false') <> 'true'
""",

    "template_records.sql": """
SELECT
    r.id as record_id,
    to_date2(r.js ->> 'date'::text) AS record_dt,
    to_date2month(r.js ->> 'date'::text) AS record_dt_month,
    to_date2year(r.js ->> 'date'::text) AS record_dt_year,
    (r.js->'client'->>'id')::int AS client_id
FROM records r
WHERE COALESCE(r.js->>'deleted', 'false') <> 'true'
""",

    "template_active_cards.sql": """
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
	', ') "[card] Активные абонементы",
  sum((ac.js->>'united_balance_services_count')::int) as "[card] Занятий по абонементам, клв",
  min((ac.js->>'created_date')::date) as "[card] Покупка абонементов, дата",
  to_char(min((ac.js->>'created_date')::date), 'YYYY-MM') as "[card] Покупка абонементов, месяц",
  min((ac.js->>'activated_date')::date) as "[card] Активация абонементов, дата",
  to_char(min((ac.js->>'activated_date')::date), 'YYYY-MM') as "[card] Активация абонементов, месяц",
  max((ac.js->>'expiration_date')::date) as "[card] Окончание абонементов, дата",
  to_char(max((ac.js->>'expiration_date')::date), 'YYYY-MM') as "[card] Окончание абонементов, месяц",
  sum(ac.costs) as "[card] Сумма продажи, руб",
  count(*) as "[card] Активных абонементов, клв"
from active_cards ac join detail_clients2 cl on cl.id = ac.client_id
group by cl.id
""",

    "template_clients.sql": """
select
  cl.id client_id,
  concat(
    case
      when length(cl.js->>'phone') = 12 then left(cl.js->>'phone', 5) || '•••' || right(cl.js->>'phone', 4)
      else cl.js->>'phone'
    end,
    ' ',
    cl.js->>'display_name'
  ) as "[client]‍🦳 Клиент",
  concat(
    cl.js->>'phone',
    ' ',
    cl.js->>'display_name'
  ) as "[client]‍🦳 Клиент, unmasked",
  round(cast(cl.js->>'paid' as decimal)) as "[client]‍🦳 Сумма по клиенту, руб",
  round(cast(cl.js->>'visits' as decimal)) as "[client]‍🦳 Визитов клиента, раз"
from detail_clients2 cl""",

    "template_workflow2.sql": """
select
  w.name "[workflow] Воронка",
  w.opened_at::date as "[workflow] Создана воронка, дата",
  to_char(w.opened_at::date, 'YYYY-MM') as "[workflow] Создана воронка, месяц",
  to_char(w.opened_at::date, 'YYYY') as "[workflow] Создана воронка, год",
  case
    when w.closed_at::date is null
	then 'Open'
	else 'Close'
  end "[workflow] Статус воронки",
  w.closed_at::date as "[workflow] Воронка завершена, дата",
  to_char(w.closed_at::date, 'YYYY-MM') as "[workflow] Воронка завершена, месяц",
  to_char(w.closed_at::date, 'YYYY') as "[workflow] Воронка завершена, год",
  (w.data->>'client_id')::int client_id,
  --dc.js->>'display_name' as "[workflow] Клиент",
  --dc.js->>'phone' as "[workflow] Телефон",
  ws.stage_name as "[workflow] Задача",
  ws.created_at::date as "[workflow] Открыта задача, дата",
  to_char(ws.created_at::date, 'YYYY-MM') as "[workflow] Открыта задача, месяц",
  to_char(ws.created_at::date, 'YYYY') as "[workflow] Открыта задача, год",
  to_char(ws.started_at::timestamp, 'DD.MM.YYYY HH24:MI:SS') as "[workflow] Запустить задачу в",
  EXTRACT(DAY FROM (coalesce(w.closed_at::timestamp, current_timestamp) - (w.opened_at::timestamp))) as "[workflow] Длительность, дней",
  to_char((w.closed_at::timestamp) - (w.opened_at::timestamp), 'FMDD "дней" HH24:MI:SS') "[workflow] Длительность"
from workflow2 w
, workflow_stages2 ws
, detail_clients2 dc
where ws.id = (select max(id) from workflow_stages2 ws where ws.workflow_id = w.id)
  and dc.id = (w.data->>'client_id')::int
--  and w.opened_at::date between {{ begin_date }} and {{ end_date }}
order by 1, 2, 3, 4""",
}
