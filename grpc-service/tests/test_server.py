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
    billingAddress="Test Street 1, 12345 City",
)
TESTRECHNUNG.items.add(description="Consulting", quantity=2.0, unitPrice=50.0, totalPrice=100.0)


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
    assert daten["billingAddress"] == "Test Street 1, 12345 City"
    assert len(daten["items"]) == 1
    assert daten["items"][0]["description"] == "Consulting"


def test_rechnung_speichern_leere_id(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.SpeichereRechnungsmetadaten(invoice_pb2.Rechnungsmetadaten(invoiceId="", billingAddress="Straße"), kontext)

    assert kontext.statuscode == grpc.StatusCode.INVALID_ARGUMENT


def test_rechnung_speichern_leerzeichen_id(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.SpeichereRechnungsmetadaten(invoice_pb2.Rechnungsmetadaten(invoiceId="   ", billingAddress="Straße"), kontext)

    assert kontext.statuscode == grpc.StatusCode.INVALID_ARGUMENT


def test_rechnung_speichern_leere_adresse(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    rechnung = invoice_pb2.Rechnungsmetadaten(invoiceId="INV-001", billingAddress="")
    dienst.SpeichereRechnungsmetadaten(rechnung, kontext)

    assert kontext.statuscode == grpc.StatusCode.INVALID_ARGUMENT
    assert "Rechnungsadresse" in kontext.meldung


def test_rechnung_speichern_gleiche_adresse_andere_id_erlaubt(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()

    dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, ScheinKontext())

    rechnung2 = invoice_pb2.Rechnungsmetadaten(
        invoiceId="INV-TEST-002",
        billingAddress="Test Street 1, 12345 City",
    )
    kontext = ScheinKontext()
    antwort = dienst.SpeichereRechnungsmetadaten(rechnung2, kontext)

    assert kontext.statuscode is None
    assert antwort.success is True
    assert antwort.invoiceId == "INV-TEST-002"
    assert (tmp_path / "INV-TEST-002.json").exists()


def test_rechnung_speichern_doppelte_id(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()

    dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, ScheinKontext())

    # Zweite speichern mit gleicher ID, aber anderer Adresse (sollte am ID-Check scheitern)
    rechnung2 = invoice_pb2.Rechnungsmetadaten(
        invoiceId="INV-TEST-001",
        billingAddress="Other Street 2",
    )
    kontext = ScheinKontext()
    dienst.SpeichereRechnungsmetadaten(rechnung2, kontext)

    assert kontext.statuscode == grpc.StatusCode.ALREADY_EXISTS


def test_rechnung_abrufen_gefunden(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()

    dienst.SpeichereRechnungsmetadaten(TESTRECHNUNG, ScheinKontext())

    anfrage = invoice_pb2.RechnungsAnfrage(invoiceId="INV-TEST-001")
    ergebnis = dienst.HoleRechnungsmetadaten(anfrage, ScheinKontext())

    assert ergebnis.invoiceId == "INV-TEST-001"
    assert ergebnis.supplierName == "Test GmbH"
    assert ergebnis.currency == "EUR"
    assert ergebnis.billingAddress == "Test Street 1, 12345 City"
    assert len(ergebnis.items) == 1
    assert ergebnis.items[0].description == "Consulting"


def test_rechnung_abrufen_nicht_gefunden(tmp_path, monkeypatch):
    monkeypatch.setattr("server.SPEICHER", tmp_path)
    dienst = RechnungsService()
    kontext = ScheinKontext()

    dienst.HoleRechnungsmetadaten(invoice_pb2.RechnungsAnfrage(invoiceId="GIBT-ES-NICHT"), kontext)

    assert kontext.statuscode == grpc.StatusCode.NOT_FOUND
