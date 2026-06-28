"""Zeebe-Job-Handler, der einen Zahlungsauftrag per RabbitMQ sendet.

Aufgaben (Subtasks 4.5–4.6, KAN-267/268):
  - Zeebe-Prozessvariablen via payment_mapping ins Zahlungsauftrag-Schema
    ueberfuehren
  - Bestehenden payment_producer aus Sprint 1 wiederverwenden
    (client/src/payment_producer.py)
  - Fehler klassifizieren:
      * Mapping/Datenfehler  → BusinessError → BPMN Error Boundary Event
      * AMQP/Broker-Fehler   → Exception     → Zeebe-Retry, danach Incident
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pika
from pyzeebe.errors import BusinessError

from mapping.payment_mapping import MappingFehler, variablen_zu_zahlungsauftrag

_HIER = Path(__file__).resolve().parent
_SPRINT1_CLIENT_SRC = _HIER.parent.parent.parent / "client" / "src"
sys.path.insert(0, str(_SPRINT1_CLIENT_SRC))

from payment_producer import sende_zahlungsauftrag  # noqa: E402

logger = logging.getLogger(__name__)

JOB_TYPE_ZAHLUNG_SENDEN = "send-payment-order"
JOB_TIMEOUT_MS = 30_000

# BPMN-Error-Code — muss mit dem Error Boundary Event am Service-Task
# "send-payment-order" im BPMN (Error_RabbitMQ_ID, errorCode "ERR_RABBITMQ")
# uebereinstimmen. Boundary fuehrt zur User-Task "Zahlung manuell erfassen".
ERROR_CODE_RABBITMQ = "ERR_RABBITMQ"


async def handle_zahlung_senden(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `send-payment-order`.

    Rueckgabe: Dict mit Prozessvariable `paymentRequested`.
    """
    invoice_id = variablen.get("invoiceId", "<ohne ID>")
    logger.info("[%s] Job empfangen fuer Rechnung %s",
                JOB_TYPE_ZAHLUNG_SENDEN, invoice_id)

    try:
        rechnung = variablen_zu_zahlungsauftrag(variablen)
    except MappingFehler as fehler:
        logger.error("[%s] Mapping fehlgeschlagen fuer %s: %s",
                     JOB_TYPE_ZAHLUNG_SENDEN, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_RABBITMQ, str(fehler))

    try:
        await asyncio.to_thread(
            sende_zahlungsauftrag, rechnung, rechnung["invoiceId"]
        )
    except pika.exceptions.AMQPConnectionError as fehler:
        logger.error("[%s] RabbitMQ nicht erreichbar fuer %s: %s",
                     JOB_TYPE_ZAHLUNG_SENDEN, invoice_id, fehler)
        raise
    except pika.exceptions.AMQPError as fehler:
        logger.error("[%s] AMQP-Fehler fuer %s: %s",
                     JOB_TYPE_ZAHLUNG_SENDEN, invoice_id, fehler)
        raise
    except Exception as fehler:
        logger.error("[%s] Unerwarteter Fehler fuer %s: %s",
                     JOB_TYPE_ZAHLUNG_SENDEN, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_RABBITMQ, f"Unerwarteter Fehler: {str(fehler)}")

    logger.info("[%s] Zahlungsauftrag gesendet fuer %s, Betrag: %s %s",
                JOB_TYPE_ZAHLUNG_SENDEN, invoice_id,
                rechnung["amountGross"], rechnung["currency"])

    return {"paymentRequested": True}


def registriere_payment_handler(worker) -> None:
    """Registriert den Zahlungs-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_ZAHLUNG_SENDEN,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_zahlung_senden)