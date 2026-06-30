import pika
import json
import time
import os
import random
from datetime import datetime, timezone
from pathlib import Path

BROKER = os.getenv("BROKER_ADRESSE", "amqp://admin:admin@localhost/")
WARTESCHLANGE = "zahlungsauftraege"
LOG_DATEI = Path(__file__).parent.parent.parent / "Rechnungsdaten" / "zahlungslog.json"


def protokolliere_status(auftrag: dict, status: str):
    eintrag = {
        "invoiceId": auftrag["invoiceId"],
        "status":    status,
        "zeitpunkt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "betrag":    auftrag["amount"],
        "waehrung":  auftrag["currency"],
    }
    if "billingAddress" in auftrag:
        eintrag["billingAddress"] = auftrag["billingAddress"]
    if "items" in auftrag:
        eintrag["items"] = auftrag["items"]

    protokoll = []
    if LOG_DATEI.exists():
        try:
            protokoll = json.loads(LOG_DATEI.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            protokoll = []

    LOG_DATEI.parent.mkdir(exist_ok=True)
    protokoll.append(eintrag)
    LOG_DATEI.write_text(json.dumps(protokoll, indent=2), encoding="utf-8")


PFLICHTFELDER = ["invoiceId", "supplierName", "iban", "amount", "currency"]


def validiere_auftrag(auftrag: dict) -> str | None:
    for feld in PFLICHTFELDER:
        if feld not in auftrag or auftrag[feld] == "" or auftrag[feld] is None:
            return f"Pflichtfeld fehlt oder ist leer: '{feld}'"
    if not isinstance(auftrag["amount"], (int, float)) or auftrag["amount"] <= 0:
        return f"Ungültiger Betrag: {auftrag['amount']!r} (muss > 0 sein)"
    if not str(auftrag["iban"]).strip():
        return "IBAN darf nicht leer sein"
    return None


def verarbeite_zahlung(kanal, methode, eigenschaften, nachricht):
    try:
        auftrag = json.loads(nachricht)
    except json.JSONDecodeError as e:
        print(f"[Zahlungssystem] Ungültige JSON-Nachricht, wird verworfen: {e}")
        kanal.basic_nack(delivery_tag=methode.delivery_tag, requeue=False)
        return

    fehler = validiere_auftrag(auftrag)
    if fehler:
        print(f"[Zahlungssystem] Validierungsfehler — Auftrag wird verworfen: {fehler}")
        kanal.basic_nack(delivery_tag=methode.delivery_tag, requeue=False)
        return

    print("\n[Zahlungssystem] Neuer Zahlungsauftrag:")
    print(f"  Rechnungs-ID : {auftrag['invoiceId']}")
    print(f"  Lieferant    : {auftrag['supplierName']}")
    print(f"  IBAN         : {auftrag['iban']}")
    print(f"  Betrag       : {auftrag['amount']} {auftrag['currency']}")
    print(f"  Fällig       : {auftrag['dueDate']}")
    if "billingAddress" in auftrag:
        print(f"  Adresse      : {auftrag['billingAddress']}")
    if "items" in auftrag and auftrag["items"]:
        print(f"  Positionen   : {json.dumps(auftrag['items'], indent=2)}")

    protokolliere_status(auftrag, "RECEIVED")
    time.sleep(0.5) # Simuliere kurze Bearbeitungszeit

    if random.random() > 0.8:
        protokolliere_status(auftrag, "FAILED")
        print(f"[Zahlungssystem] Zahlung FEHLGESCHLAGEN, Status in {LOG_DATEI.name} protokolliert")
    else:
        protokolliere_status(auftrag, "PROCESSED")
        print(f"[Zahlungssystem] Zahlung erfolgreich, Status in {LOG_DATEI.name} protokolliert")

    kanal.basic_ack(delivery_tag=methode.delivery_tag)


def starte_consumer():
    while True:
        try:
            verbindungsparameter = pika.URLParameters(BROKER)
            verbindung = pika.BlockingConnection(verbindungsparameter)
            kanal = verbindung.channel()
            kanal.queue_declare(queue=WARTESCHLANGE, durable=True)
            kanal.basic_qos(prefetch_count=1)
            kanal.basic_consume(queue=WARTESCHLANGE, on_message_callback=verarbeite_zahlung)
            print(f"[Zahlungssystem] Warte auf Nachrichten in '{WARTESCHLANGE}' ...")
            kanal.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("[Zahlungssystem] Verbindung fehlgeschlagen, Neuversuch in 5s ...")
            time.sleep(5)


if __name__ == "__main__":
    starte_consumer()
