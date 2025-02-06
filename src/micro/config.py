from bestconfig import Config

config = Config()

OPENAPI = config.get("OPENAPI", None)

# Заснуть после ошибки
SLEEP_AFTER_ERROR_SECOND = config.get("SLEEP_AFTER_ERROR_SECOND", 120)

# Номер нашей сети
CHAIN_ID = config.CHAIN_ID
# Номер филиала
COMPANY_ID = config.COMPANY_ID
# Логин и токин подключеня к API
YCLIENT_LOGIN = config.YCLIENT_LOGIN
YCLIENT_PASSWORD = config.YCLIENT_PASSWORD
PARTNER_TOKEN = config.PARTNER_TOKEN
PAGE_COUNT = int(config.PAGE_COUNT)

# Подключение к БД
PG_DATABASE = config.DB_PG_BASE
PG_HOST = config.DB_PG_HOST
#
PG_USER = config.DB_PG_USR_RW
PG_PASSWORD = config.DB_PG_PWD_RW
PG_PORT = config.DB_PG_PORT

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
