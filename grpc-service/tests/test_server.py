import json
import pytest
import grpc
import invoice_pb2
from server import RechnungsService


class ScheinKontext:
    def __init__(self):
        self.statuscode = None
        self.meldung = None

    def set_code(self, code):
        self.statuscode = code

    def set_details(self, details):
        self.meldung = details


TESTRECHNUNG = invoice_pb2.Rechnungsmetadaten(
    invoiceId="INV-TEST-001",
    supplierId="SUP-1",
    supplierName="Test GmbH",
    invoiceDate="2026-01-01",
    dueDate="2026-02-01",
    amountNet=100.0,
    amountGross=119.0,
    currency="EUR",
    iban="DE00000000000000000000",
    status="OPEN",
    fileName="test.pdf",
    createdAt="2026-01-01T00:00:00Z",
)


def test_rechnung_speichern_erfolgreich(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    antwort = dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, kontext)

    assert antwort.success is True
    assert antwort.invoiceId == "INV-TEST-001"


def test_rechnung_speichern_erstellt_datei(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()

    dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, ScheinKontext())

    datei = tmp_path / "INV-TEST-001.json"
    assert datei.exists()

    daten = json.loads(datei.read_text())
    assert daten["invoiceId"] == "INV-TEST-001"
    assert daten["supplierName"] == "Test GmbH"
    assert daten["amountGross"] == 119.0


def test_rechnung_speichern_leere_id(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.SpeichereRechnungsmetadaten(invoice_pb2.Rechnungsmetadaten(invoiceId=""), kontext)

    assert kontext.statuscode == grpc.StatusCode.INVALID_ARGUMENT


def test_rechnung_speichern_leerzeichen_id(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.SpeichereRechnungsmetadaten(invoice_pb2.Rechnungsmetadaten(invoiceId="   "), kontext)

    assert kontext.statuscode == grpc.StatusCode.INVALID_ARGUMENT


def test_rechnung_abrufen_gefunden(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()

    dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, ScheinKontext())

    anfrage = invoice_pb2.RechnungsAnfrage(invoiceId="INV-TEST-001")
    ergebnis = dienst.HoleRechnungsmetadaten(anfrage, ScheinKontext())

    assert ergebnis.invoiceId == "INV-TEST-001"
    assert ergebnis.supplierName == "Test GmbH"
    assert ergebnis.currency == "EUR"


def test_rechnung_abrufen_nicht_gefunden(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.HoleRechnungsmetadaten(invoice_pb2.RechnungsAnfrage(invoiceId="GIBT-ES-NICHT"), kontext)

    assert kontext.statuscode == grpc.StatusCode.NOT_FOUND
