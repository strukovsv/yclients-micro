from __future__ import annotations

import logging
from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

import micro.pg_ext as base

from micro.models.header_event import HeaderEvent, PrintBaseEvent

logger = logging.getLogger(__name__)


class EndCardsPrint(PrintBaseEvent):
    """Распечатать окончивающиеся абонементы"""

    pass
