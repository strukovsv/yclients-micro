from __future__ import annotations

import logging
from typing import Any, List, Optional

from pydantic_avro.base import AvroBase
from pydantic import Field, BaseModel

import micro.pg_ext as base

from micro.models.header_event import HeaderEvent

logger = logging.getLogger(__name__)


class PaymentBaseClass(HeaderEvent):
    """Базовый класс для платежей"""


class PaymentWriteTransaction(PaymentBaseClass):
    """Провести платежную транзакцию"""

    # fmt: off
    sum: int = Field(..., description="Сумма платежа") # noqa
    expense_id: int = Field(..., description="Статбя платежа") # noqa
    comment: str = Field(..., description="Комментарий платежа") # noqa
    # fmt: on

