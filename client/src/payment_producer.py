import json
import os
import pika
from datetime import datetime, timezone

BROKER = os.getenv("BROKER_ADRESSE", "amqp://admin:admin@localhost/")
WARTESCHLANGE = "zahlungsauftraege"


def erstelle_zahlungsauftrag(rechnung: dict, bestaetigte_id: str) -> dict:
    return {
        "invoiceId":    bestaetigte_id,
        "supplierId":   rechnung["supplierId"],
        "supplierName": rechnung["supplierName"],
        "iban":         rechnung["iban"],
        "amount":       rechnung["amountGross"],
        "currency":     rechnung["currency"],
        "dueDate":      rechnung["dueDate"],
        "timestamp":    datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def sende_zahlungsauftrag(rechnung: dict, bestaetigte_id: str):
    auftrag = erstelle_zahlungsauftrag(rechnung, bestaetigte_id)

    print(f"[Zahlungsversand] Sende Zahlungsauftrag an {BROKER}, Warteschlange: {WARTESCHLANGE}")
    print(f"[Zahlungsversand] Rechnung: {auftrag['invoiceId']}, Betrag: {auftrag['amount']} {auftrag['currency']}")

    try:
        verbindungsparameter = pika.URLParameters(BROKER)
        verbindung = pika.BlockingConnection(verbindungsparameter)
    except pika.exceptions.AMQPConnectionError:
        print(f"[Zahlungsversand] Broker nicht erreichbar ({BROKER}). Läuft RabbitMQ?")
        raise

    try:
        kanal = verbindung.channel()
        kanal.queue_declare(queue=WARTESCHLANGE, durable=True)
        kanal.basic_publish(
            exchange="",
            routing_key=WARTESCHLANGE,
            body=json.dumps(auftrag).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        verbindung.close()

    print(f"[Zahlungsversand] Zahlungsauftrag gesendet für Rechnung: {bestaetigte_id}")
