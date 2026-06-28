"""Zeebe-Job-Handler, der eine Rueckfrage an den Lieferanten "sendet".

Service-Task `send-information-request` (Pfad approvalDecision = "INFO_REQUIRED").
Es gibt keine echte Lieferanten-Schnittstelle, daher wird die Rueckfrage als
Datensatz in Rechnungsdaten/<invoiceId>_rueckfrage.json protokolliert. Danach
wartet der Prozess am Event-Gateway auf Message_Antwort bzw. den Timer.

Fehlerklassifizierung (Task hat im BPMN KEINE Error-Boundary):
  * invoiceId fehlt/leer      -> BusinessError -> Incident (Safety-Net)
  * Dateisystem-Fehler        -> Exception     -> Zeebe-Retry, danach Incident
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from pyzeebe.errors import BusinessError

_PRODUKTIONSWURZEL = Path(__file__).resolve().parent.parent.parent.parent
_ARCHIV_ORDNER = _PRODUKTIONSWURZEL / "Rechnungsdaten"

JOB_TYPE_RUECKFRAGE = "send-information-request"
JOB_TIMEOUT_MS = 30_000

ERROR_CODE_RUECKFRAGE = "ERR_INFO_REQUEST"

logger = logging.getLogger(__name__)


async def handle_rueckfrage_senden(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `send-information-request`.

    Rueckgabe: Dict mit Prozessvariable `infoRequestSent`.
    """
    invoice_id = variablen.get("invoiceId", None)
    if not invoice_id or (isinstance(invoice_id, str) and not invoice_id.strip()):
        raise BusinessError(ERROR_CODE_RUECKFRAGE,
                            "invoiceId fehlt oder ist leer bei Rueckfrage")

    invoice_id = str(invoice_id).strip()
    logger.info("[%s] Rueckfrage gestartet fuer Rechnung %s",
                JOB_TYPE_RUECKFRAGE, invoice_id)

    rueckfrage = {
        "invoiceId": invoice_id,
        "status": "RUECKFRAGE_GESENDET",
        "zeitpunkt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "empfaenger": variablen.get("supplierEmail", ""),
        "approvalComment": variablen.get("approvalComment", ""),
    }

    datei_pfad = _ARCHIV_ORDNER / f"{invoice_id}_rueckfrage.json"

    try:
        content = json.dumps(rueckfrage, indent=2, ensure_ascii=False)
        await asyncio.to_thread(_datei_schreiben, datei_pfad, content)
    except OSError as fehler:
        logger.error("[%s] Dateisystem-Fehler fuer %s: %s",
                     JOB_TYPE_RUECKFRAGE, invoice_id, fehler)
        raise
    except Exception as fehler:
        logger.error("[%s] Unerwarteter Fehler fuer %s: %s",
                     JOB_TYPE_RUECKFRAGE, invoice_id, fehler)
        return {"infoRequestSent": False, "infoRequestError": str(fehler)}

    logger.info("[%s] Rueckfrage protokolliert: %s", JOB_TYPE_RUECKFRAGE, datei_pfad)
    return {"infoRequestSent": True}


def _datei_schreiben(pfad: Path, content: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(content)


def registriere_info_request_handler(worker) -> None:
    """Registriert den Rueckfrage-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_RUECKFRAGE,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_rueckfrage_senden)
