from __future__ import annotations

import logging
from pydantic import Field

from micro.models.header_event import HeaderEvent, PrintBaseEvent

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


class PaymentWriteTransaction2(PaymentBaseClass):
    """Провести платежную транзакцию по шаблону"""

    # fmt: off
    sum: int = Field(..., description="Сумма платежа") # noqa
    payments_id: int = Field(..., description="Шаблон платежа") # noqa
    # fmt: on


class PaymentDbtPrint(PrintBaseEvent):
    """Распечатать приход"""

    pass


class PaymentCrdPrint(PrintBaseEvent):
    """Распечатать расход"""

    pass


class PaymentOborotPrint(PrintBaseEvent):
    """Распечатать свернутые денежные обороты"""

    pass


class PaymentMoneyPrint(PrintBaseEvent):
    """Распечатать приход и расход денежных средств"""

    pass
