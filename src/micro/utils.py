import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def hide_passwords(value: dict, key: str = None) -> dict:
    """Скрыть пароли и токены в словаре

    :param dict value: исходный словарь
    :param str key: Ключ
    :return dict: преобразованный словарь
    """
    if value is None:
        return None
    elif isinstance(value, dict):
        return {k: hide_passwords(v, k) for k, v in value.items()}
    elif isinstance(value, list):
        return [hide_passwords(elem) for elem in value]
    else:
        if key:
            for key_denied in ["PASS", "TOKEN", "ACCESS_KEY", "PWD"]:
                if key_denied in key.upper():
                    return "<hidden>"
        return value


def getenv(name: str, default: str = None):
    if name:
        value = os.environ.get(name.upper(), None)
        if value:
            return value.replace("\r", "").replace("\n", "").rstrip()
        else:
            return default
    else:
        return None


def get_period(type_period: str, sformat: str = None, current_date=None):
    # now = datetime.now() + timedelta(hours=7)
    now = current_date if current_date else datetime.now()
    arr = type_period.split("-")
    if len(arr) == 2 and arr[0].isdigit():
        num = int(arr[0])
        name = arr[1]
    else:
        num = None
    if type_period.lower() == "yesterday":
        date1 = now - timedelta(days=1)
        date2 = date1
    elif type_period.lower() == "week":
        date1 = now - timedelta(days=7)
        date2 = now
    elif num is not None and name == "week":
        # День на следующей недели
        dt = now + timedelta(days=(7 * num))
        date1 = dt - timedelta(days=dt.weekday())
        date2 = date1 + timedelta(days=6)
    elif type_period.lower() == "current-week":
        date1 = now - timedelta(days=now.weekday())
        date2 = date1 + timedelta(days=6)
    elif type_period.lower() == "prev-week":
        # День на следующей недели
        dt = now - timedelta(days=7)
        date1 = dt - timedelta(days=dt.weekday())
        date2 = date1 + timedelta(days=6)
    elif type_period.lower() == "next-week":
        # День на следующей недели
        dt = now + timedelta(days=7)
        date1 = dt - timedelta(days=dt.weekday())
        date2 = date1 + timedelta(days=6)
    elif type_period.lower() == "prev-month":
        dt = now.replace(day=1)
        date2 = dt - timedelta(days=1)
        date1 = date2.replace(day=1)
    elif type_period.lower() == "month":
        date1 = now.replace(day=1)
        date2 = now
    elif type_period.lower() == "tomorrow":
        date1 = now + timedelta(days=1)
        date2 = date1
    else:  # message["type"] == "now"
        date1 = now
        date2 = date1
    if sformat:
        return (date1.strftime(sformat), date2.strftime(sformat))
    else:
        return (date1, date2)


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
