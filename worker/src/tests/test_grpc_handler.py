"""Tests fuer handlers.grpc_handler."""
from unittest.mock import patch

import grpc
import pytest
from pyzeebe.errors import BusinessError

from handlers.grpc_handler import (
    ERROR_CODE_GRPC,
    handle_grpc_speichern,
)


def vollstaendige_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-099",
        "invoiceNumber": "RE-2026-099",
        "supplierName": "Beispiel AG",
        "invoiceDate": "2026-04-10",
        "amountGross": 595.00,
        "currency": "EUR",
        "channel": "EMAIL",
        "billingAddress": "Musterweg 1, 12345 Musterstadt",
        "fileName": "rechnung.pdf",
        "dueDate": "2026-05-10",
        "iban": "DE12345678901234567890",
        "amountNet": 500.00,
    }


class FakeRpcError(grpc.RpcError):
    def __init__(self, code, details=""):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


@pytest.mark.asyncio
async def test_happy_path_gibt_metadata_stored_zurueck():
    with patch("handlers.grpc_handler.speichere_rechnung",
               return_value="INV-CONFIRMED-001") as mock_grpc:
        ergebnis = await handle_grpc_speichern(**vollstaendige_variablen())

    assert ergebnis == {"metadataStored": True, "confirmedInvoiceId": "INV-CONFIRMED-001"}
    mock_grpc.assert_called_once()
    uebergeben = mock_grpc.call_args.args[0]
    assert uebergeben["invoiceId"] == "INV-2026-099"
    assert uebergeben["amountGross"] == 595.00


@pytest.mark.asyncio
async def test_mapping_fehler_wird_zu_business_error_invalid_data():
    variablen = vollstaendige_variablen()
    del variablen["invoiceNumber"]

    with pytest.raises(BusinessError) as info:
        await handle_grpc_speichern(**variablen)

    assert info.value.error_code == ERROR_CODE_GRPC
    assert "invoiceNumber" in str(info.value)


@pytest.mark.asyncio
async def test_grpc_invalid_argument_wird_zu_business_error():
    fehler = FakeRpcError(grpc.StatusCode.INVALID_ARGUMENT, "leere ID")
    with patch("handlers.grpc_handler.speichere_rechnung", side_effect=fehler):
        with pytest.raises(BusinessError) as info:
            await handle_grpc_speichern(**vollstaendige_variablen())

    assert info.value.error_code == ERROR_CODE_GRPC


@pytest.mark.asyncio
async def test_grpc_already_exists_wird_zu_business_error():
    fehler = FakeRpcError(grpc.StatusCode.ALREADY_EXISTS, "doppelte Rechnung")
    with patch("handlers.grpc_handler.speichere_rechnung", side_effect=fehler):
        with pytest.raises(BusinessError) as info:
            await handle_grpc_speichern(**vollstaendige_variablen())

    assert info.value.error_code == ERROR_CODE_GRPC


@pytest.mark.asyncio
async def test_grpc_unavailable_wird_re_raised_fuer_zeebe_retry():
    fehler = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "Server weg")
    with patch("handlers.grpc_handler.speichere_rechnung", side_effect=fehler):
        with pytest.raises(grpc.RpcError):
            await handle_grpc_speichern(**vollstaendige_variablen())


@pytest.mark.asyncio
async def test_grpc_deadline_exceeded_wird_re_raised():
    fehler = FakeRpcError(grpc.StatusCode.DEADLINE_EXCEEDED, "Timeout")
    with patch("handlers.grpc_handler.speichere_rechnung", side_effect=fehler):
        with pytest.raises(grpc.RpcError):
            await handle_grpc_speichern(**vollstaendige_variablen())


@pytest.mark.asyncio
async def test_grpc_internal_wird_re_raised():
    fehler = FakeRpcError(grpc.StatusCode.INTERNAL, "Server-Bug")
    with patch("handlers.grpc_handler.speichere_rechnung", side_effect=fehler):
        with pytest.raises(grpc.RpcError):
            await handle_grpc_speichern(**vollstaendige_variablen())


@pytest.mark.asyncio
async def test_runtime_error_aus_grpc_client_wird_business_error():
    with patch("handlers.grpc_handler.speichere_rechnung",
               side_effect=RuntimeError("Service-Fehler: Validierung")):
        with pytest.raises(BusinessError) as info:
            await handle_grpc_speichern(**vollstaendige_variablen())

    assert info.value.error_code == ERROR_CODE_GRPC
