"""pyzeebe-Worker fuer den Sprint-4-Workflow.

Verbindet sich mit Zeebe (Camunda 8) und abonniert alle Service-Task-Job-Types:
  - save-invoice-metadata    gRPC-Metadaten speichern
  - send-payment-order       RabbitMQ-Zahlungsauftrag senden
  - archive-invoice          Prozessabschluss archivieren
"""
import asyncio
import logging
import os
from pathlib import Path

from pyzeebe import ZeebeWorker, create_insecure_channel

from handlers.archive_handler import registriere_archive_handler
from handlers.grpc_handler import registriere_grpc_handler
from handlers.info_request_handler import registriere_info_request_handler
from handlers.payment_handler import registriere_payment_handler

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")

_HIER = Path(__file__).resolve().parent
_LOG_DATEI = _HIER.parent / "worker.log"

logger = logging.getLogger("worker")


def _logging_konfigurieren() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_LOG_DATEI, encoding="utf-8"),
        ],
    )


async def main() -> None:
    _logging_konfigurieren()
    logger.info("Starte Worker, verbinde mit Zeebe: %s", ZEEBE_ADRESSE)

    kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
    worker = ZeebeWorker(kanal)

    registriere_grpc_handler(worker)
    registriere_payment_handler(worker)
    registriere_archive_handler(worker)
    registriere_info_request_handler(worker)

    logger.info(
        "Worker bereit, abonniere Job-Types: "
        "save-invoice-metadata, send-payment-order, archive-invoice, "
        "send-information-request"
    )
    await worker.work()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker beendet (Strg+C)")