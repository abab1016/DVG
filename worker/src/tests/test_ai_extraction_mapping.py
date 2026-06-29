import pytest
from mapping.ai_extraction_mapping import (
    MappingFehler,
    pruefe_plausibilitaet,
    ai_daten_zu_prozessvariablen,
)


def valid_ai_data() -> dict:
    return {
      "invoiceId": "INV-2026-140",
      "invoiceNumber": "RE-2026-140",
      "supplierName": "DVG Lieferant GmbH",
      "invoiceDate": "2026-06-20",
      "dueDate": "2026-07-20",
      "amountGross": 595.00,
      "amountNet": 500.00,
      "currency": "EUR",
      "iban": "DE89370400440532013000",
      "billingAddress": "Hauptstrasse 12, 12345 Berlin",
      "confidence": {
        "invoiceId": 0.95,
        "invoiceNumber": 0.98,
        "supplierName": 0.99,
        "invoiceDate": 0.97,
        "amountGross": 0.95,
        "currency": 0.99,
        "iban": 0.96,
        "billingAddress": 0.92
      },
      "sourceFile": "INV-2026-140.pdf",
      "extractionEngine": "n8n+gemini-1.5"
    }


def test_happy_path_validation():
    status, reasons = pruefe_plausibilitaet(valid_ai_data())
    assert status == "VALID"
    assert len(reasons) == 0


def test_missing_mandatory_field():
    data = valid_ai_data()
    del data["supplierName"]
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("supplierName" in r for r in reasons)


def test_empty_mandatory_field():
    data = valid_ai_data()
    data["invoiceNumber"] = "   "
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("invoiceNumber" in r for r in reasons)


def test_low_confidence_value():
    data = valid_ai_data()
    data["confidence"]["iban"] = 0.84
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("iban" in r and "under the threshold" or "unter der Schwelle" in r for r in reasons)


def test_missing_confidence_dict():
    data = valid_ai_data()
    del data["confidence"]
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("Confidence-Objekt fehlt" in r for r in reasons)


def test_missing_single_confidence_value():
    data = valid_ai_data()
    del data["confidence"]["currency"]
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("Confidence für Feld 'currency' fehlt" in r for r in reasons)


def test_negative_amounts():
    data = valid_ai_data()
    data["amountGross"] = -100.00
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("amountGross darf nicht negativ sein" in r for r in reasons)


def test_gross_smaller_than_net():
    data = valid_ai_data()
    data["amountGross"] = 400.00
    data["amountNet"] = 500.00
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("amountGross" in r and "amountNet" in r for r in reasons)


def test_invalid_currency_format():
    data = valid_ai_data()
    data["currency"] = "EURO"
    status, reasons = pruefe_plausibilitaet(data)
    assert status == "NEEDS_REVIEW"
    assert any("currency" in r or "Währung" in r for r in reasons)


def test_invoice_id_muss_zum_demo_dateinamen_passen():
    data = valid_ai_data()
    data["invoiceId"] = "INV-2026-999"

    status, reasons = pruefe_plausibilitaet(data)

    assert status == "NEEDS_REVIEW"
    assert any("Dateinamen" in reason and "INV-2026-140" in reason for reason in reasons)


def test_beliebiger_dateiname_erzwingt_keine_invoice_id():
    data = valid_ai_data()
    data["sourceFile"] = "eingangsrechnung-kunde.pdf"

    status, reasons = pruefe_plausibilitaet(data)

    assert status == "VALID"
    assert reasons == []


def test_structural_failure():
    with pytest.raises(MappingFehler):
        pruefe_plausibilitaet("not-a-dict")


def test_mapping_to_process_variables():
    data = valid_ai_data()
    vars = ai_daten_zu_prozessvariablen(data)
    
    assert vars["channel"] == "EMAIL"
    assert vars["fileName"] == "INV-2026-140.pdf"
    assert vars["aiPlausibilityStatus"] == "VALID"
    assert vars["aiReviewGruende"] == ""
    assert vars["invoiceId"] == "INV-2026-140"
    assert "confidence" not in vars


def test_mapping_with_errors_to_process_variables():
    data = valid_ai_data()
    data["confidence"]["iban"] = 0.50
    vars = ai_daten_zu_prozessvariablen(data)
    
    assert vars["aiPlausibilityStatus"] == "NEEDS_REVIEW"
    assert "iban" in vars["aiReviewGruende"]
