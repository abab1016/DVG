import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grpc_client import speichere_rechnung
from payment_producer import sende_zahlungsauftrag

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
    "fileName":     "rechnung_2026_001.pdf",
    "createdAt":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}


def rechnung_einlesen() -> dict:
    argumente = sys.argv[1:]
    if "--datei" in argumente:
        stelle = argumente.index("--datei")
        if stelle + 1 >= len(argumente):
            print("[Client] Fehler: Nach --datei muss ein Dateipfad angegeben werden.")
            sys.exit(1)
        pfad = argumente[stelle + 1]
        print(f"[Client] Lade Rechnung aus Datei: {pfad}")
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    print("[Client] Verwende Demo-Rechnungsdaten.")
    return DEMO_RECHNUNG


def main():
    rechnung = rechnung_einlesen()
    print(f"[Client] Rechnung: {rechnung['invoiceId']}, Lieferant: {rechnung['supplierName']}, Betrag: {rechnung['amountGross']} {rechnung['currency']}")

    try:
        bestaetigte_id = speichere_rechnung(rechnung)
    except Exception as fehler:
        print(f"[Client] Fehler beim Speichern der Rechnung: {fehler}")
        sys.exit(1)

    try:
        sende_zahlungsauftrag(rechnung, bestaetigte_id)
    except Exception as fehler:
        print(f"[Client] Fehler beim Senden des Zahlungsauftrags: {fehler}")
        sys.exit(1)

    print(f"[Client] Rechnung {bestaetigte_id} gespeichert und Zahlungsauftrag gesendet.")


if __name__ == "__main__":
    main()
