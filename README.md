# micro

Общий набор Python-библиотек для микросервисов проекта Happiness. Пакет
объединяет обработку событий Kafka, доступ к PostgreSQL, основу HTTP-сервиса
на FastAPI, формирование отчётов и интеграции с внешними API.

Требуется **Python 3.11 или новее**. Версия в `pyproject.toml` — `0.0.7`.
Лицензия — [MIT](LICENSE).

## Состав пакета

| Модули | Назначение |
| --- | --- |
| `service` | FastAPI-приложение, фоновый цикл обработки Kafka, состояние сервиса и HTTP-метрики |
| `kafka_consumer`, `kafka_producer` | Чтение пакетов сообщений, обработчики событий, отправка JSON, DLQ и перехват отправки для outbox |
| `models/`, `schemes`, `events` | Pydantic-модели событий, реестр схем и обработка сообщений прежнего формата |
| `pg`, `pg_ext`, `sql_templates` | Асинхронные пулы PostgreSQL, транзакции, SQL-шаблоны и прикладные запросы |
| `migrate` | Применение миграций yoyo из каталога `migrations/` приложения |
| `render`, `render_ext`, `send_messages` | Jinja2-шаблоны, таблицы, отчёты и подготовка сообщений получателям |
| `api_yclients`, `api_fromni`, `api_github` | Интеграции с Yclients, Fromni и GitHub |
| `telegram`, `max`, `notifications`, `calendar` | Служебные уведомления и работа с CalDAV |
| `config`, `logging_trace`, `metrics`, `metrics_api`, `status`, `utils`, `singleton` | Конфигурация, трассировка, Prometheus-метрики и общие функции |

Модели в `models/` описывают события клиентов, CRM, чатов, ботов, AI,
платежей, абонементов, расписания, почты, cron и workflow.
Некоторые прикладные модули ожидают таблицы и шаблоны сервисов Happiness;
универсальную схему базы данных пакет не создаёт.

## Установка

Из корня репозитория:

```bash
python3 -m venv venv
. venv/bin/activate
python -m pip install -e .
```

Основные зависимости и их версии определены в `pyproject.toml`.
`requirements.txt` дополнительно содержит пакеты для тестов, но не фиксирует
версии. Часть используемых библиотек пока не включена в зависимости пакета;
их нужно установить для соответствующих модулей:

| Пакеты | Когда нужны |
| --- | --- |
| `bestconfig` | Импорт `micro.config`, работа с Kafka, БД и интеграциями |
| `psutil`, `uvicorn` | Запуск приложения `micro.service` и сбор метрик памяти |
| `jinja2`, `prettytable` | Шаблоны и отчёты; также импорт реестра моделей через cron-события |
| `caldav` | `micro.calendar` |
| `PyGithub` | `micro.api_github` |
| `pytest`, `pytest-asyncio`, `dictdiffer` | Запуск тестов |

Для примеров сервиса ниже:

```bash
python -m pip install bestconfig psutil uvicorn jinja2 prettytable
```

## Конфигурация

`micro.config` читает параметры через `bestconfig.Config()` при импорте.
Установите переменные окружения до запуска Python. Kafka и PostgreSQL нужны
при использовании соответствующих функций; этот репозиторий их не разворачивает.

| Переменная | Назначение / значение по умолчанию |
| --- | --- |
| `ENVIRONMENT` | `prod` / `production` включает признак production; по умолчанию `stage` |
| `SRC_BOOTSTRAP_SERVERS` | Адреса брокеров для consumer |
| `DST_BOOTSTRAP_SERVERS` | Адреса брокеров для producer |
| `SRC_GROUP_ID` | Группа consumer и идентификатор источника событий producer |
| `TOPIC` | Общий топик чтения и отправки по умолчанию |
| `SRC_PATTERN_TOPIC` | Шаблон подписки, если список топиков чтения пуст |
| `LOCAL_TOPIC` | Дополнительный локальный топик чтения |
| `DLQ_WRITE_TOPIC`, `DLQ_READ_TOPIC` | Топики отправки сообщений с ошибками и повторного чтения |
| `BATCH_TIMEOUT_SEC`, `BATCH_MAX_RECORDS` | Ожидание пакета и размер чтения: `5` секунд и `5` сообщений |
| `KAFKA_READ_TIMEOUT_SEC`, `KAFKA_DELIVERY_TIMEOUT_SEC` | Таймаут чтения и отправки: по `60` секунд |
| `DB_PG_HOST`, `DB_PG_PORT`, `DB_PG_BASE` | Хост, порт и имя PostgreSQL-базы |
| `DB_PG_USR_RW`, `DB_PG_PWD_RW` | Пользователь и пароль для запросов |
| `DB_PG_USR_OWNER`, `DB_PG_PWD_OWNER`, `DB_PG_PORT_MIGRATION` | Отдельные параметры для миграций |
| `SLEEP_AFTER_ERROR_SECOND` | Пауза фонового цикла после ошибки: `120` секунд |
| `OPENAPI` | Непустое значение включает `/openapi.json` |

Дополнительные настройки Kafka с префиксом `KAFKA_` и параметры интеграций
перечислены в [config.py](src/micro/config.py). Например, Telegram использует
`TELEGRAM_TOKEN` и `TELEGRAM_CHAT`, MAX — `MAX_TOKEN`, CalDAV — `CALDAV_URL`,
`CALDAV_USERNAME` и `CALDAV_TOKEN`.

Пример локального окружения:

```bash
export SRC_BOOTSTRAP_SERVERS=localhost:9092
export DST_BOOTSTRAP_SERVERS=localhost:9092
export SRC_GROUP_ID=example-service
export TOPIC=example.events
export DB_PG_HOST=localhost
export DB_PG_PORT=5432
export DB_PG_BASE=example
export DB_PG_USR_RW=example
export DB_PG_PWD_RW=local-password
```

## HTTP-сервис и обработчики событий

Создайте `main.py` в приложении, использующем библиотеку:

```python
import logging

from micro.service import app
from micro.kafka_consumer import event_handler
from micro.models.common_events import InfoEvent

app.service_name = "example-service"
app.summary = "example-service"
logger = logging.getLogger(__name__)


@event_handler("InfoEvent")
async def on_info(event: InfoEvent):
    logger.info("Получено сообщение: %s", event.text)
```

Для `/metrics` требуется каталог мультипроцессных метрик Prometheus.
Перед запуском задайте `PROMETHEUS_MULTIPROC_DIR`, указывающий на отдельный
доступный для записи каталог. Очищайте его перед новым запуском приложения,
когда предыдущие процессы остановлены.

```bash
mkdir -p /tmp/example-service-prometheus
export PROMETHEUS_MULTIPROC_DIR=/tmp/example-service-prometheus
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --log-config logger-plain.conf
```

Фоновый цикл читает Kafka, если задан `TOPIC` или `SRC_PATTERN_TOPIC`.
Обработчик `@event_handler` получает модель из реестра `Schema`;
`@message_handler` получает словарь, а `@all_event_handler()` — исходную запись Kafka.
Модули обработчиков и моделей должны быть импортированы до обработки сообщений.
Реестр моделей кэшируется при первом обращении.

Consumer отключает автоматический commit и при отсутствии сохранённых offset
читает новые сообщения (`latest`). Фоновый цикл фиксирует offset после обработки
пакета партиции. При заданном `DLQ_WRITE_TOPIC` ошибки обработки направляются
в DLQ с данными об ошибке и числе попыток.

| Маршрут | Назначение |
| --- | --- |
| `/health` | Состояние сервиса и uptime; ошибка возвращает HTTP 500 |
| `/metrics` | Метрики Prometheus |
| `/threading` | PID и идентификатор потока |
| `/envs` | Переменные окружения после обработки `hide_passwords` |
| `/changelog`, `/ui/changelog` | Чтение changelog; HTML при соответствующем заголовке `Accept` |

Приложение может задавать `app.runner`, `app.del_objects` и `app.healthcheck`
как асинхронные функции, а также `app.changelog` как путь к файлу истории изменений.

## Отправка событий

```python
import asyncio

from micro.kafka_producer import KafkaProducer
from micro.models.common_events import InfoEvent


async def main():
    try:
        await InfoEvent(text="Сервис готов").send(topic="example.events")
    finally:
        await KafkaProducer().stop()


asyncio.run(main())
```

`HeaderEvent.send()` формирует заголовок с именем класса события, UUID,
временем, источником и трассировкой. Аргумент `parent` связывает событие с
родительским, `topic` переопределяет топик, `key` — ключ маршрутизации.
Получателя можно задать через `client_id`, `chat_id`, `channel`, `contact_id`
или объект `Addresse`.

## PostgreSQL и транзакции

`DB` использует общий асинхронный пул с `autocommit=True` и возвращает строки
как словари. Доступны `execute`, `returning`, `fetchall`, `fetchone`.
`DB2` поддерживает пулы по строкам подключения; описанный ниже контекст
транзакции реализован в `DB`.

```python
from micro.pg import DB


async def save_items():
    db = DB()
    try:
        async with db.transaction():
            await db.execute(
                "INSERT INTO items (id, name) VALUES (%(id)s, %(name)s)",
                {"id": 1, "name": "Пример"},
            )
            row = await db.fetchone(
                "SELECT * FROM items WHERE id = %(id)s", {"id": 1}
            )
        return row
    finally:
        await db.close()
```

Пример предполагает существующую таблицу `items`. Внутри `db.transaction()`
SQL-вызовы `DB` и обёртки `pg_ext` используют одно соединение. Успешный выход
фиксирует транзакцию, исключение вызывает откат; вложенный контекст создаёт
savepoint. `db.connection()` предоставляет соединение напрямую. Контекст
транзакции нельзя использовать из другой asyncio-задачи.

`pg_ext.select()` загружает SQL-шаблоны из встроенного словаря и каталога
`sql/` либо `template_path`. Значения SQL-параметров передавайте через `params`.
`render` использует каталог `templates/` относительно рабочего каталога.
Миграции запускаются явно вызовом `await micro.migrate.execute()`.

## Перехват отправки Kafka для outbox

`defer_kafka(sender)` перенаправляет отправку из `KafkaProducer` в асинхронную
функцию `sender(topic=..., key=..., value=...)`: `key` — строка или `None`,
`value` — готовое значение сообщения (при отправке JSON — байты).

```python
from micro.kafka_producer import defer_kafka
from micro.models.common_events import InfoEvent
from micro.pg import DB


async def save_with_event(store_outbox):
    # store_outbox — функция приложения, сохраняющая сообщение через DB()
    # в его собственную таблицу outbox в текущей транзакции.
    async with DB().transaction():
        with defer_kafka(store_outbox):
            await InfoEvent(text="Изменения сохранены").send(topic="example.events")
```

Таблицу outbox, её миграции, функцию сохранения и механизм последующей доставки
реализует приложение. Контекст действует в текущей задаче и восстанавливается
при выходе; отправка из дочерней задачи с унаследованным контекстом вызывает
`RuntimeError`. Для запроса повторной доставки worker предусмотрена модель
`micro.models.cron_events.WorkerOutboxFlush` с обязательным полем `data`,
например `WorkerOutboxFlush(data={})`.

## Разработка и документация

```bash
python -m pip install pytest pytest-asyncio dictdiffer
python -m pytest tests/test_events.py tests/test_single.py tests/test_diff.py
```

Эти тесты проверяют преобразование имён событий, singleton и работу с diff;
Kafka и PostgreSQL для них не нужны. Настроек линтера в репозитории нет.

- [История изменений](changelog.md).
- [AsyncAPI](docs/ru/asyncapi.yaml) и [описание событий](docs/ru/asyncapi_events.yaml).
- Конфигурации логирования: `logger-plain.conf` и `logger-json.conf`.
- `Dockerfile` и `docker-compose.yaml` содержат вспомогательное окружение;
  текущая команда Compose запускает `tests/test_diff.py`. Перед сборкой нужно
  исправить некорректный тег базового образа в `Dockerfile`.
