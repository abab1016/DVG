"""Tests fuer handlers/human_review_handler.py (KAN-457)."""
import json

import pytest
from pyzeebe.errors import BusinessError

from handlers.human_review_handler import handle_human_review
from mapping.human_review_mapping import STATUS_REVIEWED


def _ai_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-300",
        "invoiceNumber": "RE-2026-300",
        "supplierName": "Handler GmbH",
        "invoiceDate": "2026-06-21",
        "amountGross": 595.0,
        "currency": "EUR",
        "iban": "",
        "billingAddress": "Handlerweg 2, 76133 Karlsruhe",
        "aiPlausibilityStatus": "NEEDS_REVIEW",
    }


@pytest.mark.asyncio
async def test_korrektur_als_dict():
    """humanReviewData als dict -> Korrektur uebernommen, Status REVIEWED."""
    variablen = _ai_variablen()
    variablen["humanReviewData"] = {"iban": "DE89370400440532013000"}
    ergebnis = await handle_human_review(**variablen)
    assert ergebnis["iban"] == "DE89370400440532013000"
    assert ergebnis["aiPlausibilityStatus"] == STATUS_REVIEWED
    assert ergebnis["humanReviewApplied"] is True


@pytest.mark.asyncio
async def test_korrektur_als_json_string():
    """humanReviewData als JSON-String wird geparst."""
    variablen = _ai_variablen()
    variablen["humanReviewData"] = json.dumps({"iban": "DE89370400440532013000"})
    ergebnis = await handle_human_review(**variablen)
    assert ergebnis["iban"] == "DE89370400440532013000"
    assert ergebnis["humanReviewApplied"] is True


@pytest.mark.asyncio
async def test_ohne_humanReviewData_ist_passthrough():
    """Keine Review-Variable -> kein Fehler, applied=False, IDs erhalten."""
    ergebnis = await handle_human_review(**_ai_variablen())
    assert ergebnis["humanReviewApplied"] is False
    assert ergebnis["invoiceId"] == "INV-2026-300"
    assert "aiPlausibilityStatus" not in ergebnis


@pytest.mark.asyncio
async def test_leerer_string_ist_passthrough():
    variablen = _ai_variablen()
    variablen["humanReviewData"] = "   "
    ergebnis = await handle_human_review(**variablen)
    assert ergebnis["humanReviewApplied"] is False


@pytest.mark.asyncio
async def test_business_error_bei_kaputtem_json():
    variablen = _ai_variablen()
    variablen["humanReviewData"] = "{ kein json }"
    with pytest.raises(BusinessError):
        await handle_human_review(**variablen)


@pytest.mark.asyncio
async def test_business_error_bei_falschem_typ():
    variablen = _ai_variablen()
    variablen["humanReviewData"] = [1, 2, 3]
    with pytest.raises(BusinessError):
        await handle_human_review(**variablen)


@pytest.mark.asyncio
async def test_business_error_bei_json_das_kein_objekt_ist():
    variablen = _ai_variablen()
    variablen["humanReviewData"] = json.dumps([1, 2, 3])
    with pytest.raises(BusinessError):
        await handle_human_review(**variablen)


@pytest.mark.asyncio
async def test_business_error_bei_fehlender_invoice_id():
    """Inkonsistente IDs nach Review -> BusinessError (zurueck in manuelle Bearbeitung)."""
    variablen = _ai_variablen()
    del variablen["invoiceId"]
    variablen["humanReviewData"] = {"iban": "DE89370400440532013000"}
    with pytest.raises(BusinessError):
        await handle_human_review(**variablen)
