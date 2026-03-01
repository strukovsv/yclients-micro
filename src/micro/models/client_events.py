from __future__ import annotations

import logging

from micro.models.header_event import HeaderEvent, PrintBaseEvent

logger = logging.getLogger(__name__)


class ClientPrint(PrintBaseEvent):
    """Распечатать клиентов для сотрудника и для админа"""

    pass


class ClientMarked(HeaderEvent):
    """Отмечены клиенты, что пришли"""

    pass
