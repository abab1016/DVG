import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grpc_client import speichere_rechnung
from payment_producer import sende_zahlungsauftrag

# Demo-Rechnung (entspricht dem Metadatenmodell aus dem README)
DEMO_RECHNUNG = {
    "invoiceId":    "INV-2026-001",
    "supplierId":   "SUP-123",
    "supplierName": "Muster GmbH",
    "invoiceDate":  "2026-04-06",
    "dueDate":      "2026-05-06",
    "amountNet":    1000.00,
    "amountGross":  1190.50,
    "currency":     "EUR",
    "iban":         "DE89370400440532013000",
    "status":       "OPEN",
    "fileName":     "invoice_2026_001.pdf",
    "createdAt":    datetime.utcnow().isoformat() + "Z",
}


def rechnung_einlesen() -> dict:
    args = sys.argv[1:]
    if "--file" in args:
        pfad = args[args.index("--file") + 1]
        print(f"[Client] Lese Rechnung aus: {pfad}")
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    print("[Client] Verwende Demo-Rechnungsdaten.")
    return DEMO_RECHNUNG


def main():
    print("=" * 56)
    print(" DVG-Client — Rechnungserfassung & Zahlungsauslösung")
    print("=" * 56)

    # Schritt 1: Eingabe lesen
    print("\n[Client] ── Schritt 1: Rechnungsdaten einlesen ─────────")
    rechnung = rechnung_einlesen()
    print(f"[Client] Invoice-ID  : {rechnung['invoiceId']}")
    print(f"[Client] Lieferant   : {rechnung['supplierName']}")
    print(f"[Client] Bruttobetrag: {rechnung['amountGross']} {rechnung['currency']}")

    # Schritt 2 + 3: gRPC  -> bestätigte ID
    try:
        confirmed_id = speichere_rechnung(rechnung)
    except Exception as e:
        print(f"\n[Client] ✗ Abbruch nach gRPC-Fehler: {e}")
        sys.exit(1)

    # Schritt 4: Zahlungsauftrag senden
    try:
        sende_zahlungsauftrag(rechnung, confirmed_id)
    except Exception as e:
        print(f"\n[Client] Fehler beim Senden des Zahlungsauftrags: {e}")
        sys.exit(1)

    # Abschluss
    print("\n" + "=" * 56)
    print(f" Fertig — Invoice {confirmed_id} gespeichert & Zahlung ausgelöst")
    print("=" * 56)


if __name__ == "__main__":
    main()
