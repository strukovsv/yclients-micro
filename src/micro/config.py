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
    else None
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
}
# Топик отправки сообщений
SRC_TOPIC = config.get("TOPIC", None)
DST_TOPIC = config.get("TOPIC", None)
# When set to True, the producer will ensure that exactly one copy
# of each message is written in the stream.
# If False, producer retries due to broker failures, etc.,
# may write duplicates of the retried message in the stream.
# Note that enabling idempotence acks to set to all
ENABLE_IDEMPOTENCE = True

# 1 - Автоматом делать commit чтения из KAFKA
# 0 - При вызове команды
KAFKA_ENABLE_AUTO_COMMIT = config.int("KAFKA_ENABLE_AUTO_COMMIT") == "1"
#  Максимальные период наполнения блока чтения из KAFKA
BATCH_TIMEOUT_SEC = config.int("BATCH_TIMEOUT_SEC") or 5
#  Максимальные размер блока чтения из KAFKA
BATCH_MAX_RECORDS = config.int("BATCH_MAX_RECORDS") or 5

SCHEMA_REGISTRY_URL = config.get("SCHEMA_REGISTRY_URL", None)

IMOBIS_TOKEN = config.get("IMOBIS_TOKEN", None)

# Данные бота телеграма для отправки служебных сообщений
TELEGRAM_TOKEN = config.get("TELEGRAM_TOKEN", None)
TELEGRAM_CHAT = config.get("TELEGRAM_CHAT", None)
TELEGRAM_BOT = config.get("TELEGRAM_BOT", None)

CALDAV_URL = config.get("CALDAV_URL", None)
CALDAV_USERNAME = config.get("CALDAV_USERNAME", None)
CALDAV_TOKEN = config.get("CALDAV_TOKEN", None)
