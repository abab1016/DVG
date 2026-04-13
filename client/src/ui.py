import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from grpc_client import speichere_rechnung
from payment_producer import sende_zahlungsauftrag

DEMO_DATEN = {
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
    "createdAt":    "2026-04-06T10:30:00Z",
}


def trennlinie():
    print("-" * 52)


def eingabe(bezeichnung: str, standard: str = "") -> str:
    hinweis = f" [{standard}]" if standard else ""
    wert = input(f"  {bezeichnung}{hinweis}: ").strip()
    return wert if wert else standard


def eingabe_zahl(bezeichnung: str, standard: float) -> float:
    while True:
        rohwert = eingabe(bezeichnung, str(standard))
        try:
            return float(rohwert.replace(",", "."))
        except ValueError:
            print("  Bitte eine gültige Zahl eingeben.")


def rechnung_anzeigen(rechnung: dict):
    trennlinie()
    print("  Rechnungsübersicht:")
    trennlinie()
    print(f"  Rechnungs-ID : {rechnung['invoiceId']}")
    print(f"  Lieferant    : {rechnung['supplierName']} ({rechnung['supplierId']})")
    print(f"  Rech.-datum  : {rechnung['invoiceDate']}   Fällig: {rechnung['dueDate']}")
    print(f"  Netto        : {rechnung['amountNet']:.2f} {rechnung['currency']}")
    print(f"  Brutto       : {rechnung['amountGross']:.2f} {rechnung['currency']}")
    print(f"  IBAN         : {rechnung['iban']}")
    print(f"  Dateiname    : {rechnung['fileName']}")
    trennlinie()


def verarbeite_rechnung(rechnung: dict):
    rechnung_anzeigen(rechnung)

    bestaetigung = input("  Rechnung speichern und Zahlung auslösen? [j/n]: ").strip().lower()
    if bestaetigung != "j":
        print("  Abgebrochen.")
        return

    print()
    try:
        bestaetigte_id = speichere_rechnung(rechnung)
    except Exception as fehler:
        print(f"\n  gRPC-Fehler: {fehler}")
        return

    try:
        sende_zahlungsauftrag(rechnung, bestaetigte_id)
    except Exception as fehler:
        print(f"\n  Broker-Fehler: {fehler}")
        return

    print()
    trennlinie()
    print(f"  Rechnung {bestaetigte_id} gespeichert und Zahlung ausgelöst.")
    trennlinie()


def modus_demo():
    print("\n  Demo-Rechnung wird geladen ...\n")
    demo = dict(DEMO_DATEN)
    demo["createdAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verarbeite_rechnung(demo)


def modus_manuell():
    print("\n  Rechnungsdaten eingeben (Enter = Standardwert übernehmen)\n")
    heute = datetime.today().strftime("%Y-%m-%d")
    rechnung = {
        "invoiceId":    eingabe("Rechnungs-ID", f"INV-{datetime.today().year}-001"),
        "supplierId":   eingabe("Lieferanten-ID", "SUP-001"),
        "supplierName": eingabe("Lieferantenname", "Muster GmbH"),
        "invoiceDate":  eingabe("Rechnungsdatum (JJJJ-MM-TT)", heute),
        "dueDate":      eingabe("Fälligkeitsdatum (JJJJ-MM-TT)", heute[:8] + "30"),
        "amountNet":    eingabe_zahl("Nettobetrag (EUR)", 0.00),
        "amountGross":  eingabe_zahl("Bruttobetrag (EUR)", 0.00),
        "currency":     eingabe("Währung", "EUR"),
        "iban":         eingabe("IBAN", "DE00000000000000000000"),
        "status":       "OPEN",
        "fileName":     eingabe("Dateiname", "rechnung.pdf"),
        "createdAt":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    verarbeite_rechnung(rechnung)


def modus_datei():
    pfad = input("\n  Pfad zur JSON-Datei: ").strip()
    try:
        rechnung = json.loads(Path(pfad).read_text(encoding="utf-8"))
        rechnung.setdefault("status", "OPEN")
        rechnung.setdefault("createdAt", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        verarbeite_rechnung(rechnung)
    except FileNotFoundError:
        print(f"  Datei nicht gefunden: {pfad}")
    except json.JSONDecodeError as fehler:
        print(f"  Ungültiges JSON: {fehler}")


def hauptmenue():
    print()
    trennlinie()
    print("  DVG - Eingangsrechnungsbearbeitung")
    trennlinie()

    while True:
        print()
        print("  [1]  Demo-Rechnung verarbeiten")
        print("  [2]  Rechnung manuell eingeben")
        print("  [3]  Rechnung aus JSON-Datei laden")
        print("  [0]  Beenden")
        print()
        auswahl = input("  Auswahl: ").strip()

        if auswahl == "1":
            modus_demo()
        elif auswahl == "2":
            modus_manuell()
        elif auswahl == "3":
            modus_datei()
        elif auswahl == "0":
            print("\n  Auf Wiedersehen.\n")
            sys.exit(0)
        else:
            print("  Ungültige Eingabe, bitte 0-3 wählen.")


if __name__ == "__main__":
    hauptmenue()
