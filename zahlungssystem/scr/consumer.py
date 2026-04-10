import pika
import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path

BROKER = os.getenv("BROKER_ADRESSE", "amqp://guest:guest@localhost/")
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

    protokoll = []
    if LOG_DATEI.exists():
        try:
            protokoll = json.loads(LOG_DATEI.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            protokoll = []

    LOG_DATEI.parent.mkdir(exist_ok=True)
    protokoll.append(eintrag)
    LOG_DATEI.write_text(json.dumps(protokoll, indent=2), encoding="utf-8")


def verarbeite_zahlung(kanal, methode, eigenschaften, nachricht):
    auftrag = json.loads(nachricht)
    print("\n[Zahlungssystem] Neuer Zahlungsauftrag:")
    print(f"  Rechnungs-ID : {auftrag['invoiceId']}")
    print(f"  Lieferant    : {auftrag['supplierName']}")
    print(f"  IBAN         : {auftrag['iban']}")
    print(f"  Betrag       : {auftrag['amount']} {auftrag['currency']}")
    print(f"  Fällig       : {auftrag['dueDate']}")

    protokolliere_status(auftrag, "BEZAHLT")
    print(f"[Zahlungssystem] Zahlung ausgeführt, Status in {LOG_DATEI.name} protokolliert")
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
