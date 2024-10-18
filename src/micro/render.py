import logging

from .restdb import get_data
from .utils import get_period

import jinja2
import prettytable as pt

logger = logging.getLogger(__name__)

templates = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))


async def to_prettytable(rows: list, **kwarg) -> str:
    caption = kwarg.get("caption", None)
    caption = (
        f"{caption}\n" if caption and kwarg.get("print_caption", 1) else ""
    )
    if rows:
        table = pt.PrettyTable()
        table.padding_width = 0
        table.field_names = rows[0]
        for i in range(0, len(rows[0])):
            table.align[rows[0][i]] = (
                "l" if isinstance(rows[1][i], str) else "r"
            )
        table.add_rows(rows[1:])
        return caption + table.get_string()
    else:
        if kwarg.get("print_empty", 1):
            # empty tables
            return caption + "Нет данных"
        return None


async def to_text(template: str, **kwarg) -> str:
    return templates.get_template(template).render(**kwarg)
