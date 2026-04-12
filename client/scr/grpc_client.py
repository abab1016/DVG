import grpc
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "grpc-service" / "src"))
import invoice_pb2
import invoice_pb2_grpc

GRPC_ADRESSE = os.getenv("GRPC_ADRESSE", "localhost:50051")
ZEITLIMIT_SEK = float(os.getenv("GRPC_ZEITLIMIT", "5"))


def speichere_rechnung(rechnung: dict) -> str:
    print(f"[gRPC-Client] Sende Rechnungsdaten an {GRPC_ADRESSE} ...")
    print(f"[gRPC-Client] Rechnungs-ID: {rechnung['invoiceId']}, Lieferant: {rechnung['supplierName']}")

    kanal = grpc.insecure_channel(GRPC_ADRESSE)
    stub = invoice_pb2_grpc.RechnungsServiceStub(kanal)
    anfrage = invoice_pb2.Rechnungsmetadaten(**rechnung)

    try:
        antwort = stub.SpeichereRechnungsmetadaten(anfrage, timeout=ZEITLIMIT_SEK)
    except grpc.RpcError as fehler:
        kanal.close()
        _fehler_ausgeben(fehler)
        raise

    kanal.close()

    if not antwort.success:
        raise RuntimeError(f"Service-Fehler: {antwort.message}")

    print(f"[gRPC-Client] Gespeichert, bestätigte Rechnungs-ID: {antwort.invoiceId}")
    return antwort.invoiceId


def _fehler_ausgeben(fehler: grpc.RpcError):
    statuscode = fehler.code()
    meldung = fehler.details() or str(fehler)

    if statuscode == grpc.StatusCode.UNAVAILABLE:
        print(f"[gRPC-Client] Server nicht erreichbar ({GRPC_ADRESSE}). Läuft der gRPC-Service?")
    elif statuscode == grpc.StatusCode.DEADLINE_EXCEEDED:
        print(f"[gRPC-Client] Zeitüberschreitung nach {ZEITLIMIT_SEK}s, Server antwortet nicht.")
    elif statuscode == grpc.StatusCode.INVALID_ARGUMENT:
        print(f"[gRPC-Client] Ungültige Eingabe: {meldung}")
    elif statuscode == grpc.StatusCode.INTERNAL:
        print(f"[gRPC-Client] Interner Server-Fehler: {meldung}")
    else:
        print(f"[gRPC-Client] Fehler [{statuscode.name}]: {meldung}")
