import grpc
import json
from concurrent import futures
from pathlib import Path

import invoice_pb2
import invoice_pb2_grpc

SPEICHER = Path(__file__).resolve().parent.parent.parent / "Rechnungsdaten"
SPEICHER.mkdir(exist_ok=True)


class RechnungsService(invoice_pb2_grpc.RechnungsServiceServicer):

    def SpeichereRechnungsmetadaten(self, request, context):
        if not request.invoiceId.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Rechnungs-ID darf nicht leer sein.")
            return invoice_pb2.SpeicherAntwort()

        if not request.billingAddress.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Rechnungsadresse darf nicht leer sein.")
            return invoice_pb2.SpeicherAntwort()

        # Duplikatsprüfung für Rechnungsadresse
        try:
            for pfad in SPEICHER.glob("*.json"):
                if pfad.stem == request.invoiceId:
                    continue
                try:
                    inhalt = json.loads(pfad.read_text(encoding="utf-8"))
                    if inhalt.get("billingAddress", "").strip() == request.billingAddress.strip():
                        context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                        context.set_details("Rechnungsadresse ist doppelt.")
                        return invoice_pb2.SpeicherAntwort()
                except Exception:
                    pass
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return invoice_pb2.SpeicherAntwort()

        items = []
        for item in request.items:
            items.append({
                "description": item.description,
                "quantity": item.quantity,
                "unitPrice": item.unitPrice,
                "totalPrice": item.totalPrice,
            })

        daten = {
            "invoiceId":      request.invoiceId,
            "supplierId":     request.supplierId,
            "supplierName":   request.supplierName,
            "invoiceDate":    request.invoiceDate,
            "dueDate":        request.dueDate,
            "amountNet":      request.amountNet,
            "amountGross":    request.amountGross,
            "currency":       request.currency,
            "iban":           request.iban,
            "status":         request.status,
            "fileName":       request.fileName,
            "createdAt":      request.createdAt,
            "billingAddress": request.billingAddress,
            "items":          items,
        }

        try:
            datei = SPEICHER / f"{request.invoiceId}.json"
            if datei.exists():
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details(f"Rechnung {request.invoiceId} existiert bereits.")
                return invoice_pb2.SpeicherAntwort()
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
        datei: Path = SPEICHER / f"{request.invoiceId}.json"
        if not datei.exists():
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"{request.invoiceId} nicht gefunden.")
            return invoice_pb2.Rechnungsmetadaten()

        daten = json.loads(datei.read_text(encoding="utf-8"))
        items_data = daten.pop("items", [])
        
        rechnung = invoice_pb2.Rechnungsmetadaten(**daten)
        for item in items_data:
            rechnung.items.add(
                description=item.get("description", ""),
                quantity=float(item.get("quantity", 0.0)),
                unitPrice=float(item.get("unitPrice", 0.0)),
                totalPrice=float(item.get("totalPrice", 0.0)),
            )
        return rechnung


def main():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    invoice_pb2_grpc.add_RechnungsServiceServicer_to_server(RechnungsService(), server)
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    print("[gRPC-Server] Läuft auf Port 50051")
    print(f"[gRPC-Server] Speicherort: {SPEICHER}")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
