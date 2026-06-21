import json
from pathlib import Path

import pytest

from mapping.ai_extraction_mapping import (
    STATUS_NEEDS_REVIEW,
    STATUS_VALID,
    MappingFehler,
    ai_daten_zu_prozessvariablen,
    pruefe_plausibilitaet,
)

_BEISPIEL_ORDNER = Path(__file__).resolve().parent.parent / "mapping" / "beispiele"


def vollstaendige_ai_daten() -> dict:
    return {
        "invoiceId": "INV-2026-101",
        "invoiceNumber": "RE-2026-101",
        "supplierName": "Muster GmbH",
        "invoiceDate": "2026-06-10",
        "dueDate": "2026-07-10",
        "amountGross": 1190.50,
        "amountNet": 1000.00,
        "currency": "EUR",
        "iban": "DE89370400440532013000",
        "billingAddress": "Musterweg 1, 12345 Musterstadt",
        "invoiceItems": [
            {"description": "Beratung", "quantity": 2, "unitPrice": 500.0, "totalPrice": 1000.0}
        ],
        "confidence": {
            "invoiceId": 0.98,
            "invoiceNumber": 0.97,
            "supplierName": 0.96,
            "invoiceDate": 0.99,
            "amountGross": 0.95,
            "currency": 0.99,
            "iban": 0.93,
            "billingAddress": 0.94,
        },
        "sourceFile": "rechnung_muster_gmbh_juni.pdf",
    }


# --- pruefe_plausibilitaet --------------------------------------------------

def test_happy_path_liefert_valid_ohne_gruende():
    status, gruende = pruefe_plausibilitaet(vollstaendige_ai_daten())
    assert status == STATUS_VALID
    assert gruende == []


def test_fehlendes_pflichtfeld_liefert_needs_review():
    daten = vollstaendige_ai_daten()
    del daten["iban"]
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_NEEDS_REVIEW
    assert any("iban" in g for g in gruende)


def test_niedrige_confidence_liefert_needs_review():
    daten = vollstaendige_ai_daten()
    daten["confidence"]["invoiceNumber"] = 0.5
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_NEEDS_REVIEW
    assert any("invoiceNumber" in g for g in gruende)


def test_fehlende_confidence_angabe_liefert_needs_review():
    daten = vollstaendige_ai_daten()
    del daten["confidence"]["amountGross"]
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_NEEDS_REVIEW
    assert any("amountGross" in g for g in gruende)


def test_negativer_betrag_liefert_review_grund():
    daten = vollstaendige_ai_daten()
    daten["amountNet"] = -10.0
    _, gruende = pruefe_plausibilitaet(daten)
    assert any("negativ" in g for g in gruende)


def test_brutto_kleiner_netto_liefert_review_grund():
    daten = vollstaendige_ai_daten()
    daten["amountNet"] = 5000.0
    _, gruende = pruefe_plausibilitaet(daten)
    assert any("kleiner als amountNet" in g for g in gruende)


def test_nicht_numerischer_betrag_liefert_review_statt_fehler():
    daten = vollstaendige_ai_daten()
    daten["amountGross"] = "nicht-lesbar"
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_NEEDS_REVIEW
    assert any("amountGross" in g and "nicht numerisch" in g for g in gruende)


def test_ungueltige_waehrung_liefert_review_grund():
    daten = vollstaendige_ai_daten()
    daten["currency"] = "EURO"
    _, gruende = pruefe_plausibilitaet(daten)
    assert any("Waehrung" in g for g in gruende)


def test_falscher_typ_wirft_mapping_fehler():
    with pytest.raises(MappingFehler):
        pruefe_plausibilitaet(["kein", "dict"])


# --- ai_daten_zu_prozessvariablen -------------------------------------------

def test_mapping_liefert_canonical_prozessvariablen():
    variablen = ai_daten_zu_prozessvariablen(vollstaendige_ai_daten())
    assert variablen["invoiceId"] == "INV-2026-101"
    assert variablen["channel"] == "EMAIL"
    assert variablen["fileName"] == "rechnung_muster_gmbh_juni.pdf"
    assert variablen["aiPlausibilityStatus"] == STATUS_VALID
    assert variablen["aiReviewGruende"] == []


def test_mapping_uebernimmt_status_und_gruende_bei_review_fall():
    daten = vollstaendige_ai_daten()
    del daten["iban"]
    variablen = ai_daten_zu_prozessvariablen(daten)
    assert variablen["aiPlausibilityStatus"] == STATUS_NEEDS_REVIEW
    assert any("iban" in g for g in variablen["aiReviewGruende"])
    assert "iban" not in variablen


def test_mapping_reicht_invoice_items_durch():
    variablen = ai_daten_zu_prozessvariablen(vollstaendige_ai_daten())
    assert variablen["invoiceItems"][0]["description"] == "Beratung"


def test_mapping_wirft_fehler_bei_falschem_typ():
    with pytest.raises(MappingFehler):
        ai_daten_zu_prozessvariablen("kein-dict")


# --- Beispieldateien (KAN-452 / KAN-453) -------------------------------------

def test_beispiel_happy_path_datei_ist_valid():
    daten = json.loads((_BEISPIEL_ORDNER / "ai_extraktion_happy_path.json").read_text(encoding="utf-8"))
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_VALID
    assert gruende == []


def test_beispiel_human_review_datei_ist_needs_review():
    daten = json.loads((_BEISPIEL_ORDNER / "ai_extraktion_human_review.json").read_text(encoding="utf-8"))
    status, gruende = pruefe_plausibilitaet(daten)
    assert status == STATUS_NEEDS_REVIEW
    assert len(gruende) >= 2
