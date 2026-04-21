from bestconfig import Config

config = Config()

# ENVIRONMENT=production
production = config.get("ENVIRONMENT", "stage") in ["prod", "production"]

OPENAPI = config.get("OPENAPI", None)

# Заснуть после ошибки
SLEEP_AFTER_ERROR_SECOND = config.get("SLEEP_AFTER_ERROR_SECOND", 120)

# Номер нашей сети
CHAIN_ID = config.get("CHAIN_ID", None)
# Номер филиала
COMPANY_ID = config.get("COMPANY_ID", None)
# Логин и токин подключеня к API
YCLIENT_LOGIN = config.get("YCLIENT_LOGIN", None)
YCLIENT_PASSWORD = config.get("YCLIENT_PASSWORD", None)
PARTNER_TOKEN = config.get("PARTNER_TOKEN", None)
PAGE_COUNT = (
    int(config.get("PAGE_COUNT", None))
    if config.get("PAGE_COUNT", None)
    else 25
)
IMOBIS_TOKEN = config.get("IMOBIS_TOKEN", None)

# Подключение к БД
PG_DATABASE = config.get("DB_PG_BASE", None)
PG_HOST = config.get("DB_PG_HOST", None)
#
PG_USER = config.get("DB_PG_USR_RW", None)
PG_PASSWORD = config.get("DB_PG_PWD_RW", None)
PG_PORT = config.get("DB_PG_PORT", None)

# Подключение к кафка
CONSUMER_KAFKA = {
    # Обязательные параметры подключения
    "bootstrap_servers": config.get("SRC_BOOTSTRAP_SERVERS", None),
    "group_id": config.get("SRC_GROUP_ID", None),
}

PRODUCER_ID = config.get("SRC_GROUP_ID", None)
# Подключение к кафка
PRODUCER_KAFKA = {
    # Обязательные параметры подключения
    "bootstrap_servers": config.get("DST_BOOTSTRAP_SERVERS", None),
    # Гарантирует, что каждое сообщение будет записано в партицию
    # ровно один раз (в пределах одной сессии продюсера).
    # Исключает дубликаты при повторных отправках из-за
    # сетевых сбоев или ретраев
    "enable_idempotence": config.bool("KAFKA_ENABLE_IDEMPOTENCE") or True,
    # Лидер партиции ждёт подтверждения от всех синхронных реплик (ISR),
    # прежде чем ответить продюсеру
    "acks": config.get("KAFKA_ACKS", "all"),
    # Пауза между последовательными ретраями (в миллисекундах).
    # Не экспоненциальная, а фиксированная
    "retry_backoff_ms": config.int("KAFKA_RETRY_BACKOFF_MS") or 300,
    # Максимальное время ожидания ответа от брокера на один запрос.
    # Если ответ не пришёл за это время, считается ошибкой и
    # запускается ретрай.
    "request_timeout_ms": config.int("KAFKA_REQUEST_TIMEOUT_MS") or 30000,
    # Продюсер ждёт до 10 мс, чтобы накопить несколько сообщений в один batch.
    # Увеличивает пропускную способность ценой небольшой задержки
    "linger_ms": config.int("KAFKA_LINGER_MS") or 10,
    # Сжимает батчи сообщений, снижая сетевой трафик и нагрузку на брокеры.
    # Snappy даёт хорошее сжатие при малом CPU overhead.
    # Для текстовых данных (JSON, логи) – обязателен.
    "compression_type": config.get("KAFKA_COMPRESSION_TYPE", None),
    # Время жизни метаданных (информация о партициях, лидерах)
    "metadata_max_age_ms": config.int("KAFKA_METADATA_MAX_AGE_MS") or 300000,
    # Время простоя соединения с брокером, после которого оно закрывается
    "connections_max_idle_ms": config.int("KAFKA_CONNECTIONS_MAX_IDLE_MS")
    or 540000,
}
# timeout отправки сообщений в kafka
KAFKA_DELIVERY_TIMEOUT_SEC = config.int("KAFKA_DELIVERY_TIMEOUT_SEC") or 60
# Топик отправки сообщений
SRC_TOPIC = config.get("TOPIC", None)
DST_TOPIC = config.get("TOPIC", None)
SRC_PATTERN_TOPIC = config.get("SRC_PATTERN_TOPIC", None)
DLQ_WRITE_TOPIC = config.get("DLQ_WRITE_TOPIC", None)
DLQ_READ_TOPIC = config.get("DLQ_READ_TOPIC", None)
LOCAL_TOPIC = config.get("LOCAL_TOPIC", None)

# 1 - Автоматом делать commit чтения из KAFKA
# 0 - При вызове команды
KAFKA_ENABLE_AUTO_COMMIT = config.int("KAFKA_ENABLE_AUTO_COMMIT") == "1"
#  Максимальные период наполнения блока чтения из KAFKA
BATCH_TIMEOUT_SEC = config.int("BATCH_TIMEOUT_SEC") or 5
#  Максимальные размер блока чтения из KAFKA
BATCH_MAX_RECORDS = config.int("BATCH_MAX_RECORDS") or 5

IMOBIS_TOKEN = config.get("IMOBIS_TOKEN", None)

# Данные бота телеграма для отправки служебных сообщений
TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN", None)
TELEGRAM_CHAT = config.get("TELEGRAM_CHAT", None)

CALDAV_URL = config.get("CALDAV_URL", None)
CALDAV_USERNAME = config.get("CALDAV_USERNAME", None)
CALDAV_TOKEN = config.get("CALDAV_TOKEN", None)

IMOBIS_HTTP_PROXY = config.get("HTTP_PROXY", None)
