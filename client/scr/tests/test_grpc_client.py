import pytest
from unittest.mock import patch, MagicMock
import grpc
import grpc_client

TESTRECHNUNG = {
    "invoiceId":    "INV-TEST-001",
    "supplierId":   "SUP-1",
    "supplierName": "Test GmbH",
    "invoiceDate":  "2026-01-01",
    "dueDate":      "2026-02-01",
    "amountNet":    100.0,
    "amountGross":  119.0,
    "currency":     "EUR",
    "iban":         "DE00000000000000000000",
    "status":       "OPEN",
    "fileName":     "test.pdf",
    "createdAt":    "2026-01-01T00:00:00Z",
}


class ScheinRpcFehler(grpc.RpcError):
    def __init__(self, statuscode):
        self._statuscode = statuscode

    def code(self):
        return self._statuscode

    def details(self):
        return "Testfehler"


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_gibt_rechnungs_id_zurueck(mock_stub_klasse, mock_kanal):
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.return_value = MagicMock(
        success=True,
        invoiceId="INV-TEST-001",
        message="OK"
    )
    mock_stub_klasse.return_value = mock_stub

    ergebnis = grpc_client.speichere_rechnung(TESTRECHNUNG)

    assert ergebnis == "INV-TEST-001"


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_schliesst_kanal(mock_stub_klasse, mock_kanal):
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.return_value = MagicMock(
        success=True, invoiceId="INV-TEST-001", message="OK"
    )
    mock_stub_klasse.return_value = mock_stub

    grpc_client.speichere_rechnung(TESTRECHNUNG)

    mock_kanal.return_value.close.assert_called_once()


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_server_nicht_erreichbar(mock_stub_klasse, mock_kanal):
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.side_effect = ScheinRpcFehler(grpc.StatusCode.UNAVAILABLE)
    mock_stub_klasse.return_value = mock_stub

    with pytest.raises(grpc.RpcError):
        grpc_client.speichere_rechnung(TESTRECHNUNG)


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_zeitueberschreitung(mock_stub_klasse, mock_kanal):
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.side_effect = ScheinRpcFehler(grpc.StatusCode.DEADLINE_EXCEEDED)
    mock_stub_klasse.return_value = mock_stub

    with pytest.raises(grpc.RpcError):
        grpc_client.speichere_rechnung(TESTRECHNUNG)


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_ungueltige_eingabe(mock_stub_klasse, mock_kanal):
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.side_effect = ScheinRpcFehler(grpc.StatusCode.INVALID_ARGUMENT)
    mock_stub_klasse.return_value = mock_stub

    with pytest.raises(grpc.RpcError):
        grpc_client.speichere_rechnung(TESTRECHNUNG)


@patch("grpc_client.grpc.insecure_channel")
@patch("grpc_client.invoice_pb2_grpc.RechnungsServiceStub")
def test_speichere_rechnung_service_meldet_fehler(mock_stub_klasse, mock_kanal):
    # Server antwortet mit success=False statt einem gRPC-Fehler
    mock_stub = MagicMock()
    mock_stub.SpeichereRechnungsmetadaten.return_value = MagicMock(
        success=False,
        invoiceId="",
        message="Speichern fehlgeschlagen"
    )
    mock_stub_klasse.return_value = mock_stub

    with pytest.raises(RuntimeError, match="Service-Fehler"):
        grpc_client.speichere_rechnung(TESTRECHNUNG)
