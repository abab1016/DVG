import json
import pytest
from unittest.mock import MagicMock
from consumer import verarbeite_zahlung, protokolliere_status

TESTAUFTRAG = {
    "invoiceId":    "INV-2026-001",
    "supplierName": "Muster GmbH",
    "iban":         "DE89370400440532013000",
    "amount":       1190.50,
    "currency":     "EUR",
    "dueDate":      "2026-05-06",
}


def test_verarbeite_zahlung_bestaetigt_nachricht():
    mock_kanal = MagicMock()
    mock_methode = MagicMock()
    mock_methode.delivery_tag = 42

    verarbeite_zahlung(mock_kanal, mock_methode, None, json.dumps(TESTAUFTRAG).encode())

    mock_kanal.basic_ack.assert_called_once_with(delivery_tag=42)


def test_verarbeite_zahlung_gibt_daten_aus(capsys):
    mock_kanal = MagicMock()
    mock_methode = MagicMock()
    mock_methode.delivery_tag = 1

    verarbeite_zahlung(mock_kanal, mock_methode, None, json.dumps(TESTAUFTRAG).encode())

    ausgabe = capsys.readouterr().out
    assert "INV-2026-001" in ausgabe
    assert "Muster GmbH" in ausgabe
    assert "1190.5" in ausgabe


def test_verarbeite_zahlung_kein_ack_bei_json_fehler():
    mock_kanal = MagicMock()
    mock_methode = MagicMock()

    verarbeite_zahlung(mock_kanal, mock_methode, None, b"kein json")

    mock_kanal.basic_nack.assert_called_once_with(delivery_tag=mock_methode.delivery_tag, requeue=False)
    mock_kanal.basic_ack.assert_not_called()


def test_verarbeite_zahlung_kein_ack_bei_fehlenden_feldern():
    mock_kanal = MagicMock()
    mock_methode = MagicMock()
    
    unvollstaendiger_auftrag = {"invoiceId": "INV-123"} # Es fehlen Pflichtfelder

    verarbeite_zahlung(mock_kanal, mock_methode, None, json.dumps(unvollstaendiger_auftrag).encode())

    mock_kanal.basic_nack.assert_called_once_with(delivery_tag=mock_methode.delivery_tag, requeue=False)
    mock_kanal.basic_ack.assert_not_called()


def test_protokolliere_status_schreibt_eintrag(tmp_path, monkeypatch):
    import consumer
    protokolldatei = tmp_path / "zahlungslog.json"
    monkeypatch.setattr(consumer, "LOG_DATEI", protokolldatei)

    protokolliere_status(TESTAUFTRAG, "BEZAHLT")

    protokoll = json.loads(protokolldatei.read_text())
    assert len(protokoll) == 1
    assert protokoll[0]["invoiceId"] == "INV-2026-001"
    assert protokoll[0]["status"] == "BEZAHLT"
    assert protokoll[0]["betrag"] == 1190.50


def test_protokolliere_status_haengt_eintraege_an(tmp_path, monkeypatch):
    import consumer
    protokolldatei = tmp_path / "zahlungslog.json"
    monkeypatch.setattr(consumer, "LOG_DATEI", protokolldatei)

    protokolliere_status(TESTAUFTRAG, "BEZAHLT")
    protokolliere_status({**TESTAUFTRAG, "invoiceId": "INV-2026-002"}, "BEZAHLT")

    protokoll = json.loads(protokolldatei.read_text())
    assert len(protokoll) == 2
    assert protokoll[1]["invoiceId"] == "INV-2026-002"
