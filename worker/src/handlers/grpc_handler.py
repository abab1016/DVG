"""Zeebe-Job-Handler, der Rechnungsmetadaten per gRPC speichert.

Aufgaben:
  - Zeebe-Prozessvariablen via Mapping ins Rechnungsmetadaten-Schema überführen
  - Bestehenden gRPC-Client aus Sprint 1 wiederverwenden (client/src/grpc_client.py)
  - Fehler klassifizieren:
      * Validierungs-/Datenfehler   → BusinessError → BPMN Error Boundary Event
      * Transiente gRPC-Fehler      → Exception     → Zeebe-Retry, danach Incident in Operate
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import grpc
from pyzeebe.errors import BusinessError

from failure_injection import raise_if_failure_enabled
from mapping.grpc_mapping import MappingFehler, variablen_zu_rechnung

_HIER = Path(__file__).resolve().parent
_SPRINT1_CLIENT_SRC = _HIER.parent.parent.parent / "client" / "src"
sys.path.insert(0, str(_SPRINT1_CLIENT_SRC))

from grpc_client import speichere_rechnung  # noqa: E402

logger = logging.getLogger(__name__)

JOB_TYPE_GRPC_SPEICHERN = "save-invoice-metadata"
JOB_TIMEOUT_MS = 30_000

# BPMN-Error-Code — muss mit dem Error Boundary Event am Service-Task
# "save-invoice-metadata" im BPMN (Error_gRPC_ID, errorCode "ERR_GRPC")
# uebereinstimmen. Das BPMN hat an dieser Task genau eine Fehler-Boundary
# (-> User-Task "Metadaten manuell speichern"), daher fliessen alle fachlichen
# Fehler (ungueltige Daten, Duplikat) in denselben Code.
ERROR_CODE_GRPC = "ERR_GRPC"

GRPC_BUSINESS_FEHLER = {
    grpc.StatusCode.INVALID_ARGUMENT: ERROR_CODE_GRPC,
    grpc.StatusCode.ALREADY_EXISTS: ERROR_CODE_GRPC,
    grpc.StatusCode.NOT_FOUND: ERROR_CODE_GRPC,
}


async def handle_grpc_speichern(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `save-invoice-metadata`.

    Rückgabe: Dict mit Prozessvariablen `metadataStored` und `confirmedInvoiceId`.
    """
    invoice_id = variablen.get("invoiceId", "<ohne ID>")
    logger.info("[%s] Job empfangen für Rechnung %s",
                JOB_TYPE_GRPC_SPEICHERN, invoice_id)

    raise_if_failure_enabled("grpc")

    try:
        rechnung = variablen_zu_rechnung(variablen)
    except MappingFehler as fehler:
        logger.error("[%s] Mapping fehlgeschlagen für %s: %s",
                     JOB_TYPE_GRPC_SPEICHERN, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_GRPC, str(fehler))

    MAX_VERSUCHE = 3
    letzter_fehler: grpc.RpcError | None = None
    bestaetigte_id: str = ""

    for versuch in range(1, MAX_VERSUCHE + 1):
        try:
            bestaetigte_id = await asyncio.to_thread(speichere_rechnung, rechnung)
            break
        except grpc.RpcError as fehler:
            code = fehler.code()
            details = fehler.details() or ""
            business_code = GRPC_BUSINESS_FEHLER.get(code)
            if business_code is not None:
                logger.error("[%s] Business-Fehler für %s [%s]: %s",
                             JOB_TYPE_GRPC_SPEICHERN, invoice_id, code.name, details)
                raise BusinessError(business_code, f"{code.name}: {details}")
            letzter_fehler = fehler
            logger.warning("[%s] Transienter gRPC-Fehler (Versuch %d/%d) für %s [%s]: %s",
                           JOB_TYPE_GRPC_SPEICHERN, versuch, MAX_VERSUCHE, invoice_id, code.name, details)
            if versuch < MAX_VERSUCHE:
                await asyncio.sleep(3)
        except RuntimeError as fehler:
            logger.error("[%s] Service hat success=False geliefert für %s: %s",
                         JOB_TYPE_GRPC_SPEICHERN, invoice_id, fehler)
            raise BusinessError(ERROR_CODE_GRPC, str(fehler))
    else:
        logger.error("[%s] gRPC nach %d Versuchen fehlgeschlagen für %s: %s",
                     JOB_TYPE_GRPC_SPEICHERN, MAX_VERSUCHE, invoice_id, letzter_fehler)
        raise letzter_fehler

    if not bestaetigte_id:
        raise BusinessError(ERROR_CODE_GRPC, "gRPC-Service hat keine gueltige invoiceId zurueckgegeben")

    logger.info("[%s] Rechnung gespeichert, confirmedInvoiceId=%s",
                JOB_TYPE_GRPC_SPEICHERN, bestaetigte_id)
    return {
        "metadataStored": True,
        "confirmedInvoiceId": str(bestaetigte_id),
    }


def registriere_grpc_handler(worker) -> None:
    """Registriert den gRPC-Speichern-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_GRPC_SPEICHERN,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_grpc_speichern)
