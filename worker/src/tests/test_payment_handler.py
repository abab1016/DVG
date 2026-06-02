"""Tests fuer handlers.payment_handler."""
from unittest.mock import patch

import pika
import pytest
from pyzeebe.errors import BusinessError

from handlers.payment_handler import ERROR_CODE_RABBITMQ, handle_zahlung_senden


def vollstaendige_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-099",
        "supplierName": "Beispiel AG",
        "iban": "DE12345678901234567890",
        "amountGross": 595.00,
        "currency": "EUR",
        # optional
        "supplierId": "SUP-456",
        "dueDate": "2026-05-10",
    }


@pytest.mark.asyncio
async def test_happy_path_gibt_payment_requested_zurueck():
    with patch("handlers.payment_handler.sende_zahlungsauftrag") as mock:
        ergebnis = await handle_zahlung_senden(**vollstaendige_variablen())

    assert ergebnis == {"paymentRequested": True}
    mock.assert_called_once()


@pytest.mark.asyncio
async def test_uebergibt_korrekten_betrag_an_producer():
    with patch("handlers.payment_handler.sende_zahlungsauftrag") as mock:
        await handle_zahlung_senden(**vollstaendige_variablen())

    rechnung_uebergeben = mock.call_args.args[0]
    assert rechnung_uebergeben["amountGross"] == 595.00
    assert rechnung_uebergeben["currency"] == "EUR"


@pytest.mark.asyncio
async def test_mapping_fehler_wird_zu_business_error():
    var = vollstaendige_variablen()
    del var["iban"]
    with patch("handlers.payment_handler.sende_zahlungsauftrag"):
        with pytest.raises(BusinessError) as info:
            await handle_zahlung_senden(**var)

    assert info.value.error_code == ERROR_CODE_RABBITMQ


@pytest.mark.asyncio
async def test_amqp_connection_error_wird_re_raised():
    with patch("handlers.payment_handler.sende_zahlungsauftrag",
               side_effect=pika.exceptions.AMQPConnectionError("kein Broker")):
        with pytest.raises(pika.exceptions.AMQPConnectionError):
            await handle_zahlung_senden(**vollstaendige_variablen())


@pytest.mark.asyncio
async def test_sonstiger_amqp_error_wird_re_raised():
    with patch("handlers.payment_handler.sende_zahlungsauftrag",
               side_effect=pika.exceptions.AMQPChannelError(404, "channel weg")):
        with pytest.raises(pika.exceptions.AMQPChannelError):
            await handle_zahlung_senden(**vollstaendige_variablen())
