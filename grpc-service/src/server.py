import grpc
import json
from concurrent import futures
from pathlib import Path

import invoice_pb2
import invoice_pb2_grpc

SPEICHER = Path(__file__).parent.parent.parent / "Rechnungsdaten"
SPEICHER.mkdir(exist_ok=True)


class RechnungsService(invoice_pb2_grpc.RechnungsServiceServicer):

    def SpeichereRechnungsmetadaten(self, request, context):
        if not request.invoiceId.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Rechnungs-ID darf nicht leer sein.")
            return invoice_pb2.SpeicherAntwort()

        daten = {
            "invoiceId":    request.invoiceId,
            "supplierId":   request.supplierId,
            "supplierName": request.supplierName,
            "invoiceDate":  request.invoiceDate,
            "dueDate":      request.dueDate,
            "amountNet":    request.amountNet,
            "amountGross":  request.amountGross,
            "currency":     request.currency,
            "iban":         request.iban,
            "status":       request.status,
            "fileName":     request.fileName,
            "createdAt":    request.createdAt,
        }

        try:
            datei = SPEICHER / f"{request.invoiceId}.json"
            datei.write_text(json.dumps(daten, indent=2), encoding="utf-8")
            print(f"[gRPC-Server] Gespeichert: {request.invoiceId}")
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return invoice_pb2.SpeicherAntwort()

        return invoice_pb2.SpeicherAntwort(
            invoiceId=request.invoiceId,
            success=True,
            message=f"Rechnung {request.invoiceId} gespeichert."
        )

    def HoleRechnungsmetadaten(self, request, context):
        datei = SPEICHER / f"{request.invoiceId}.json"
        if not datei.exists():
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"{request.invoiceId} nicht gefunden.")
            return invoice_pb2.Rechnungsmetadaten()

        daten = json.loads(datei.read_text(encoding="utf-8"))
        return invoice_pb2.Rechnungsmetadaten(**daten)


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    invoice_pb2_grpc.fuegeRechnungsServiceHinzu(RechnungsService(), server)
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    print("[gRPC-Server] Läuft auf Port 50051")
    print(f"[gRPC-Server] Speicherort: {SPEICHER}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
