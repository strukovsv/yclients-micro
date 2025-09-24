import os
import re
import logging
from datetime import datetime, timedelta, date

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
            for key_denied in ["PASS", "TOKEN", "ACCESS_KEY", "PWD", "SECRET"]:
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


def add_months(current_date, months_to_add):
    new_date = datetime(
        current_date.year + (current_date.month + months_to_add - 1) // 12,
        (current_date.month + months_to_add - 1) % 12 + 1,
        current_date.day,
        current_date.hour,
        current_date.minute,
        current_date.second,
    )
    return new_date


def get_period(type_period: str, sformat: str = None, current_date=None):
    # now = datetime.now() + timedelta(hours=7)
    if type_period.isdigit():
        date1 = datetime.fromisoformat(type_period)
        date2 = datetime.fromisoformat(type_period)
    else:
        now = current_date if current_date else datetime.now()
        arr = type_period.split("-")
        if len(arr) == 2 and arr[0].isdigit():
            num = int(arr[0])
            name = arr[1]
        else:
            num = None
        tp = type_period.lower()
        if tp in ["yesterday", "p1"]:
            date1 = now - timedelta(days=1)
            date2 = date1
        elif tp in ["week"]:
            date1 = now - timedelta(days=7)
            date2 = now
        elif num is not None and name == "week":
            # День на следующей недели
            dt = now + timedelta(days=(7 * num))
            date1 = dt - timedelta(days=dt.weekday())
            date2 = date1 + timedelta(days=6)
        elif tp in ["current-week", "p5"]:
            date1 = now - timedelta(days=now.weekday())
            date2 = date1 + timedelta(days=6)
        elif tp in ["prev-week", "p4"]:
            # День на следующей недели
            dt = now - timedelta(days=7)
            date1 = dt - timedelta(days=dt.weekday())
            date2 = date1 + timedelta(days=6)
        elif tp in ["next-week", "p6"]:
            # День на следующей недели
            dt = now + timedelta(days=7)
            date1 = dt - timedelta(days=dt.weekday())
            date2 = date1 + timedelta(days=6)
        elif tp in ["prev-month", "p7"]:
            dt = now.replace(day=1)
            date2 = dt - timedelta(days=1)
            date1 = date2.replace(day=1)
        elif tp in ["current-month", "p8"]:
            date1 = now.replace(day=1)
            date2 = add_months(date1, 1) - timedelta(days=1)
        elif tp in ["next-month", "p9"]:
            dt = now.replace(day=1)
            date1 = add_months(dt, 1)
            date2 = add_months(dt, 2) - timedelta(days=1)
        elif tp in ["month"]:
            date1 = now.replace(day=1)
            date2 = now
        elif tp in ["tomorrow", "p3"]:
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


def _mask_russian_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)

    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits.startswith("9"):
        digits = "7" + digits

    if len(digits) < 8:
        return phone

    first4 = digits[:4]
    last4 = digits[-4:]

    if phone.startswith("+7"):
        return f"+7{first4[1:]}•••{last4}"
    elif phone.lstrip().startswith("8"):
        return f"8{first4[1:]}•••{last4}"
    else:
        return f"{first4}•••{last4}"


def mask_phone_recursive(obj):
    """
    Рекурсивно обходит словарь (и вложенные списки/словари),
    и маскирует все значения по ключу "phone" по шаблону:
        +79233549672 → +7923•••9672
    (оставляет первые 4 символа и последние 4 цифры, середина — •••)

    Не мутирует оригинал — возвращает копию.
    """
    if isinstance(obj, dict):
        return {
            key: (
                _mask_russian_phone(value)
                if key == "phone" and isinstance(value, str)
                else mask_phone_recursive(value)
            )
            for key, value in obj.items()
        }
    elif isinstance(obj, list):
        return [mask_phone_recursive(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(mask_phone_recursive(item) for item in obj)
    else:
        return obj


def str_to_timedelta(time_str: str) -> timedelta:
    """
    Конвертирует человекочитаемую строку в объект timedelta.

    Поддерживаемые единицы:
        w — недели
        d — дни
        h — часы
        m — минуты
        s — секунды

    Пробелы необязательны. Регистр не важен.

    Примеры:
        "2h30m" → 2 часа 30 минут
        "1w 1d" → 8 дней
        "90s" → 1 минута 30 секунд

    :param time_str: Строка с временным интервалом (например, "30s", "1d2h")
    :return: Объект timedelta
    :raises ValueError: Если строка пуста или не распознана
    """
    if not isinstance(time_str, str) or not time_str.strip():
        raise ValueError("Входная строка не может быть пустой")

    # Регулярное выражение: число + необязательные пробелы + единица измерения
    pattern = r"(\d+)\s*([wdhms])"
    matches = re.findall(pattern, time_str.lower())

    if not matches:
        raise ValueError(
            f"Не удалось распознать временной интервал: {time_str}"
        )

    total_seconds = 0
    multipliers = {
        "w": 7 * 86400,  # неделя
        "d": 86400,  # день
        "h": 3600,  # час
        "m": 60,  # минута
        "s": 1,  # секунда
    }

    for value, unit in matches:
        num = int(value)
        total_seconds += num * multipliers[unit]

    return timedelta(seconds=total_seconds)
