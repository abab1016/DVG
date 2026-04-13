import json
import pytest
from unittest.mock import patch, MagicMock
import pika
from payment_producer import erstelle_zahlungsauftrag, sende_zahlungsauftrag

TESTRECHNUNG = {
    "invoiceId":    "INV-2026-001",
    "supplierId":   "SUP-123",
    "supplierName": "Muster GmbH",
    "invoiceDate":  "2026-04-06",
    "dueDate":      "2026-05-06",
    "amountNet":    1000.00,
    "amountGross":  1190.50,
    "currency":     "EUR",
    "iban":         "DE89370400440532013000",
    "status":       "OPEN",
    "fileName":     "rechnung_2026_001.pdf",
    "createdAt":    "2026-04-06T10:30:00Z",
}


def test_erstelle_zahlungsauftrag_felder():
    auftrag = erstelle_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")

    assert auftrag["invoiceId"] == "INV-2026-001"
    assert auftrag["supplierId"] == "SUP-123"
    assert auftrag["supplierName"] == "Muster GmbH"
    assert auftrag["iban"] == "DE89370400440532013000"
    assert auftrag["amount"] == 1190.50
    assert auftrag["currency"] == "EUR"
    assert auftrag["dueDate"] == "2026-05-06"
    assert "timestamp" in auftrag


def test_erstelle_zahlungsauftrag_verwendet_bestaetigte_id():
    auftrag = erstelle_zahlungsauftrag(TESTRECHNUNG, "INV-BESTAETIGT-999")
    assert auftrag["invoiceId"] == "INV-BESTAETIGT-999"


def test_erstelle_zahlungsauftrag_brutto_als_betrag():
    # Zahlungsauftrag soll Bruttobetrag enthalten, nicht Netto
    auftrag = erstelle_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")
    assert auftrag["amount"] == TESTRECHNUNG["amountGross"]
    assert auftrag["amount"] != TESTRECHNUNG["amountNet"]


@patch("payment_producer.pika.BlockingConnection")
@patch("payment_producer.pika.URLParameters")
def test_sende_zahlungsauftrag_sendet_an_warteschlange(mock_parameter, mock_verbindung):
    mock_kanal = MagicMock()
    mock_verbindung.return_value.channel.return_value = mock_kanal

    sende_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")

    mock_kanal.queue_declare.assert_called_once_with(queue="zahlungsauftraege", durable=True)
    mock_kanal.basic_publish.assert_called_once()

    argumente = mock_kanal.basic_publish.call_args[1]
    assert argumente["routing_key"] == "zahlungsauftraege"

    nachricht = json.loads(argumente["body"])
    assert nachricht["invoiceId"] == "INV-2026-001"
    assert nachricht["amount"] == 1190.50


@patch("payment_producer.pika.BlockingConnection")
@patch("payment_producer.pika.URLParameters")
def test_sende_zahlungsauftrag_dauerhaft(mock_parameter, mock_verbindung):
    mock_kanal = MagicMock()
    mock_verbindung.return_value.channel.return_value = mock_kanal

    sende_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")

    eigenschaften = mock_kanal.basic_publish.call_args[1]["properties"]
    assert eigenschaften.delivery_mode == 2


@patch("payment_producer.pika.BlockingConnection")
@patch("payment_producer.pika.URLParameters")
def test_sende_zahlungsauftrag_schliesst_verbindung(mock_parameter, mock_verbindung):
    mock_verbindung.return_value.channel.return_value = MagicMock()

    sende_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")

    mock_verbindung.return_value.close.assert_called_once()


@patch("payment_producer.pika.URLParameters")
@patch("payment_producer.pika.BlockingConnection", side_effect=pika.exceptions.AMQPConnectionError)
def test_sende_zahlungsauftrag_verbindungsfehler_wird_weitergegeben(mock_verbindung, mock_parameter):
    with pytest.raises(pika.exceptions.AMQPConnectionError):
        sende_zahlungsauftrag(TESTRECHNUNG, "INV-2026-001")
