"""Tests für pdf_handler."""
import pytest
from handlers.pdf_handler import _extrahiere_daten_aus_text, handle_pdf_auslesen


def test_extrahiere_daten_aus_text():
    text = """
    ==================================================
    RECHNUNG RE-2026-101
    Rechnungs-ID: INV-2026-101
    Rechnungsnummer: RE-2026-101
    Lieferant: DVG Lieferant GmbH
    E-Mail: lieferant@dvg.de
    Datum: 2026-06-08
    Faelligkeitsdatum: 2026-07-08
    Netto: 100.00
    Brutto: 119.00
    Waehrung: EUR
    IBAN: DE89 3704 0044 0532 0130 00
    Rechnungsadresse: Hauptstrasse 12, 12345 Berlin
    
    Positionen:
    - Consulting Dienstleistung (Quantity: 2, UnitPrice: 50.00)
    ==================================================
    """
    daten = _extrahiere_daten_aus_text(text)
    assert daten["invoiceId"] == "INV-2026-101"
    assert daten["invoiceNumber"] == "RE-2026-101"
    assert daten["supplierName"] == "DVG Lieferant GmbH"
    assert daten["supplierEmail"] == "lieferant@dvg.de"
    assert daten["invoiceDate"] == "2026-06-08"
    assert daten["dueDate"] == "2026-07-08"
    assert daten["amountNet"] == 100.0
    assert daten["amountGross"] == 119.0
    assert daten["currency"] == "EUR"
    assert daten["iban"] == "DE89370400440532013000"
    assert daten["billingAddress"] == "Hauptstrasse 12, 12345 Berlin"
    
    assert "invoiceItems" in daten
    assert isinstance(daten["invoiceItems"], str)
    assert "Consulting Dienstleistung" in daten["invoiceItems"]
    assert "2.0 x 50.0 = 100.0" in daten["invoiceItems"]


@pytest.mark.asyncio
async def test_handle_pdf_auslesen_erfolg():
    # Ruft den Handler mit der gerade erstellten beispiel_rechnung.pdf auf
    variablen = {"fileName": "beispiel_rechnung.pdf"}
    ergebnis = await handle_pdf_auslesen(**variablen)
    
    assert ergebnis["pdfSuccess"] is True
    assert ergebnis["channel"] == "EMAIL"
    assert ergebnis["invoiceId"].startswith("INV-2026-")
    assert ergebnis["supplierName"] == "DVG Lieferant GmbH"
    assert ergebnis["amountGross"] == 595.0
    assert "Hauptstrasse" in ergebnis["billingAddress"]
    assert "12345 Berlin" in ergebnis["billingAddress"]
    assert "Consulting Dienstleistung" in ergebnis["invoiceItems"]


@pytest.mark.asyncio
async def test_handle_pdf_auslesen_fehlende_datei():
    variablen = {"fileName": "datei_existiert_nicht.pdf"}
    ergebnis = await handle_pdf_auslesen(**variablen)
    assert ergebnis["pdfSuccess"] is False
    assert ergebnis["channel"] == "EMAIL"
    assert "nicht gefunden" in ergebnis["errorMessage"]
