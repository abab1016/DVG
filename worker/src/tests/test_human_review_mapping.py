"""Tests fuer mapping/human_review_mapping.py (KAN-457)."""
import pytest

from mapping.human_review_mapping import (
    STATUS_REVIEWED,
    MappingFehler,
    wende_human_review_an,
)


def _ai_variablen() -> dict:
    """Prozessvariablen, wie sie das AI-Mapping nach NEEDS_REVIEW hinterlassen haette."""
    return {
        "invoiceId": "INV-2026-200",
        "invoiceNumber": "RE-2026-200",
        "supplierName": "Beispiel GmbH",
        "invoiceDate": "2026-06-20",
        "amountGross": 1190.0,
        "amountNet": 1000.0,
        "currency": "EUR",
        "iban": "",  # unsicher erkannt -> vom Menschen zu korrigieren
        "billingAddress": "Beispielweg 1, 12345 Beispielstadt",
        "channel": "EMAIL",
        "aiPlausibilityStatus": "NEEDS_REVIEW",
        "aiReviewGruende": ["Pflichtfeld fehlt: iban"],
    }


# --- Korrektur hat Vorrang ---------------------------------------------------

def test_korrektur_gewinnt_gegen_ai_wert():
    korrekturen = {"iban": "DE89370400440532013000", "amountGross": 1200.0}
    ergebnis = wende_human_review_an(_ai_variablen(), korrekturen)
    assert ergebnis["iban"] == "DE89370400440532013000"
    assert ergebnis["amountGross"] == 1200.0
    assert set(ergebnis["humanReviewKorrekturen"]) == {"iban", "amountGross"}
    assert ergebnis["humanReviewApplied"] is True
    assert ergebnis["aiPlausibilityStatus"] == STATUS_REVIEWED
    assert ergebnis["aiReviewGruende"] == []


def test_leere_korrektur_wird_ignoriert():
    """Ein leer gelassenes Formularfeld ueberschreibt den AI-Wert NICHT."""
    korrekturen = {"iban": "   ", "supplierName": ""}
    ergebnis = wende_human_review_an(_ai_variablen(), korrekturen)
    assert "iban" not in ergebnis
    assert "supplierName" not in ergebnis
    assert ergebnis["humanReviewKorrekturen"] == []


def test_unbekanntes_feld_wird_nicht_uebernommen():
    """Fremdschluessel aus dem Formular duerfen nicht nach gRPC/RabbitMQ durchsickern."""
    korrekturen = {"hackerField": "x", "channel": "POST", "status": "PAID"}
    ergebnis = wende_human_review_an(_ai_variablen(), korrekturen)
    assert "hackerField" not in ergebnis
    assert "channel" not in ergebnis
    assert "status" not in ergebnis
    assert ergebnis["humanReviewKorrekturen"] == []


def test_unveraenderte_korrektur_zaehlt_nicht_als_aenderung():
    """Wird derselbe Wert noch einmal bestaetigt, taucht das Feld nicht in der Liste auf."""
    korrekturen = {"supplierName": "Beispiel GmbH"}  # identisch zum AI-Wert
    ergebnis = wende_human_review_an(_ai_variablen(), korrekturen)
    assert ergebnis["supplierName"] == "Beispiel GmbH"
    assert ergebnis["humanReviewKorrekturen"] == []


# --- invoiceId / invoiceNumber-Konsistenz ------------------------------------

def test_id_und_nummer_bleiben_konsistent_vorhanden():
    ergebnis = wende_human_review_an(_ai_variablen(), {"iban": "DE89370400440532013000"})
    assert ergebnis["invoiceId"] == "INV-2026-200"
    assert ergebnis["invoiceNumber"] == "RE-2026-200"


def test_korrektur_kann_invoice_nummer_setzen():
    variablen = _ai_variablen()
    del variablen["invoiceNumber"]
    ergebnis = wende_human_review_an(variablen, {"invoiceNumber": "RE-2026-999"})
    assert ergebnis["invoiceNumber"] == "RE-2026-999"
    assert "invoiceNumber" in ergebnis["humanReviewKorrekturen"]


def test_invoice_id_ist_nicht_korrigierbar():
    """invoiceId ist read-only: ein vom Formular gesetzter Wert wird ignoriert,
    der technische Korrelationsschluessel aus den Prozessvariablen gewinnt."""
    korrekturen = {"invoiceId": "INV-GEFAELSCHT", "iban": "DE89370400440532013000"}
    ergebnis = wende_human_review_an(_ai_variablen(), korrekturen)
    assert ergebnis["invoiceId"] == "INV-2026-200"  # AI-/Prozesswert bleibt
    assert "invoiceId" not in ergebnis["humanReviewKorrekturen"]
    assert ergebnis["iban"] == "DE89370400440532013000"  # andere Felder weiterhin korrigierbar


def test_fehlende_invoice_id_wirft_mapping_fehler():
    variablen = _ai_variablen()
    del variablen["invoiceId"]
    with pytest.raises(MappingFehler):
        wende_human_review_an(variablen, {"iban": "DE89370400440532013000"})


def test_fehlende_invoice_nummer_wirft_mapping_fehler():
    variablen = _ai_variablen()
    del variablen["invoiceNumber"]
    with pytest.raises(MappingFehler):
        wende_human_review_an(variablen, {"iban": "DE89370400440532013000"})


# --- Passthrough ohne Review -------------------------------------------------

def test_ohne_korrektur_passthrough_ohne_status_aenderung():
    """VALID-Pfad: keine Korrektur -> keine Statusaenderung, IDs bleiben erhalten."""
    ergebnis = wende_human_review_an(_ai_variablen(), None)
    assert ergebnis["humanReviewApplied"] is False
    assert ergebnis["humanReviewKorrekturen"] == []
    assert "aiPlausibilityStatus" not in ergebnis
    assert ergebnis["invoiceId"] == "INV-2026-200"
    assert ergebnis["invoiceNumber"] == "RE-2026-200"


def test_leeres_korrektur_objekt_gilt_als_pruefung_ohne_aenderung():
    ergebnis = wende_human_review_an(_ai_variablen(), {})
    assert ergebnis["humanReviewApplied"] is True
    assert ergebnis["humanReviewKorrekturen"] == []
    assert ergebnis["aiPlausibilityStatus"] == STATUS_REVIEWED


# --- Strukturfehler ----------------------------------------------------------

def test_korrektur_falscher_typ_wirft_mapping_fehler():
    with pytest.raises(MappingFehler):
        wende_human_review_an(_ai_variablen(), ["kein", "dict"])


def test_variablen_falscher_typ_wirft_mapping_fehler():
    with pytest.raises(MappingFehler):
        wende_human_review_an("kein-dict", {"iban": "DE89370400440532013000"})
