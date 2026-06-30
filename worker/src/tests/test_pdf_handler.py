"""Tests für pdf_handler."""
import base64
import contextlib

import pytest
from handlers import pdf_handler
from handlers.pdf_handler import (
    _extrahiere_daten_aus_text,
    _sicherer_dateiname,
    handle_pdf_auslesen,
    speichere_upload,
)


class _FakeAntwort:
    def __init__(self, daten: bytes):
        self._daten = daten

    def read(self) -> bytes:
        return self._daten


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
    assert isinstance(daten["invoiceItems"], list)
    assert len(daten["invoiceItems"]) == 1
    item = daten["invoiceItems"][0]
    assert item["description"] == "Consulting Dienstleistung"
    assert item["quantity"] == 2.0
    assert item["unitPrice"] == 50.0
    assert item["totalPrice"] == 100.0


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
    assert isinstance(ergebnis["invoiceItems"], list)
    assert any(item["description"] == "Consulting Dienstleistung" for item in ergebnis["invoiceItems"])


@pytest.mark.asyncio
async def test_handle_pdf_auslesen_fehlende_datei():
    variablen = {"fileName": "datei_existiert_nicht.pdf"}
    ergebnis = await handle_pdf_auslesen(**variablen)
    assert ergebnis["pdfSuccess"] is False
    assert ergebnis["channel"] == "EMAIL"
    assert "nicht gefunden" in ergebnis["errorMessage"]


def test_sicherer_dateiname_entfernt_pfadanteile():
    assert _sicherer_dateiname("../../etc/passwd") == "passwd"
    assert _sicherer_dateiname("C:\\temp\\rechnung.pdf") == "rechnung.pdf"
    assert _sicherer_dateiname("") == "portal_rechnung.pdf"
    assert _sicherer_dateiname("..") == "portal_rechnung.pdf"


def test_speichere_upload_camunda_dokument(tmp_path, monkeypatch):
    """Camunda-Dokument-Referenz wird per REST-API geladen und gespeichert."""
    monkeypatch.setattr(pdf_handler, "_ARCHIV_ORDNER", tmp_path)
    aufgerufene_urls = []

    @contextlib.contextmanager
    def fake_urlopen(anfrage, timeout=None):
        aufgerufene_urls.append(anfrage.full_url)
        yield _FakeAntwort(b"%PDF-1.7 fake")

    monkeypatch.setattr(pdf_handler.urllib.request, "urlopen", fake_urlopen)

    referenz = [{
        "camunda.document.type": "camunda",
        "documentId": "doc-123",
        "storeId": "in-memory",
        "metadata": {"fileName": "rechnung_portal.pdf"},
    }]
    name = speichere_upload(referenz)

    assert name == "rechnung_portal.pdf"
    assert (tmp_path / "rechnung_portal.pdf").read_bytes() == b"%PDF-1.7 fake"
    assert "/v2/documents/doc-123" in aufgerufene_urls[0]
    assert "storeId=in-memory" in aufgerufene_urls[0]


def test_speichere_upload_dokument_download_fehler_gibt_none(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_handler, "_ARCHIV_ORDNER", tmp_path)

    def fake_urlopen(anfrage, timeout=None):
        raise OSError("Verbindung verweigert")

    monkeypatch.setattr(pdf_handler.urllib.request, "urlopen", fake_urlopen)

    name = speichere_upload([{"documentId": "doc-999", "storeId": "in-memory"}])
    assert name is None


def test_speichere_upload_base64_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_handler, "_ARCHIV_ORDNER", tmp_path)
    inhalt = b"%PDF-1.4 base64 content"
    referenz = {"name": "inline.pdf", "content": base64.b64encode(inhalt).decode()}

    name = speichere_upload(referenz)

    assert name == "inline.pdf"
    assert (tmp_path / "inline.pdf").read_bytes() == inhalt


def test_speichere_upload_leer_gibt_none():
    assert speichere_upload(None) is None
    assert speichere_upload([]) is None
    assert speichere_upload([{"foo": "bar"}]) is None
