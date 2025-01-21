# Подключить логирование главного модуля
import logging

from micro.events import get_event_name

logger = logging.getLogger(__name__)


def test1():
    assert get_event_name("cards.inserted") == "cards_inserted"
    assert get_event_name("cards_inserted") == "cards_inserted"
    assert get_event_name("CardsInserted") == "cards_inserted"


def test2():
    assert get_event_name("cards$inserted") == "cards$inserted"
    assert get_event_name("cardsinserted") == "cardsinserted"
    assert get_event_name("Cardsinserted") == "cardsinserted"


def test3():
    assert (
        get_event_name("QueredReportTransactions")
        == "quered_report_transactions"
    )
