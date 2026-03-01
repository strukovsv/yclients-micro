from __future__ import annotations

import logging

from micro.models.header_event import PrintBaseEvent

logger = logging.getLogger(__name__)


class EndCardsPrint(PrintBaseEvent):
    """Распечатать окончивающиеся абонементы"""

    pass
