"""Zeebe-Job-Handler, der den Prozessabschluss archiviert.

Aufgaben (Subtask 4.7, KAN-269):
  - Schreibt eine Abschluss-JSON-Datei in den Ordner Rechnungsdaten/
  - Dateinhalt: Rechnungs-ID, Abschlussstatus, Zeitstempel
  - Fehler klassifizieren:
      * Alle Fehler (OSError, sonstige) → BusinessError → Incident in Operate
        (Der Task hat keine BPMN Error-Boundary; Incident ist das korrekte Verhalten)
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from pyzeebe.errors import BusinessError

from failure_injection import raise_if_failure_enabled

_PRODUKTIONSWURZEL = Path(__file__).resolve().parent.parent.parent.parent
_ARCHIV_ORDNER = _PRODUKTIONSWURZEL / "Rechnungsdaten"

JOB_TYPE_ARCHIVIEREN = "archive-invoice"
JOB_TIMEOUT_MS = 30_000

# Der Error-Code wird im aktuellen AI-BPMN vom Boundary Event am
# Archivierungs-Task gefangen und fuehrt zur manuellen Archivierung.
ERROR_CODE_ARCHIVE = "ERR_ARCHIVE"

logger = logging.getLogger(__name__)


async def handle_archivieren(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `archivieren`.

    Erstellt eine Abschlussdatei Rechnungsdaten/<invoiceId>_abschluss.json
    mit Prozessabschluss-Informationen.

    Rueckgabe: Dict mit Prozessvariable `archiveStatus`.
    """
    invoice_id = variablen.get("invoiceId", None)
    if not invoice_id or (isinstance(invoice_id, str) and not invoice_id.strip()):
        raise BusinessError(ERROR_CODE_ARCHIVE,
                            "invoiceId fehlt oder ist leer bei Archivierung")

    invoice_id = str(invoice_id).strip()
    logger.info("[%s] Archivierung gestartet fuer Rechnung %s",
                JOB_TYPE_ARCHIVIEREN, invoice_id)

    raise_if_failure_enabled("archive")

    abschluss = {
        "invoiceId": invoice_id,
        "status": "ABGESCHLOSSEN",
        "zeitpunkt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metadataStored": variablen.get("metadataStored", False),
        "paymentRequested": variablen.get("paymentRequested", False),
    }

    datei_pfad = _ARCHIV_ORDNER / f"{invoice_id}_abschluss.json"

    try:
        content = json.dumps(abschluss, indent=2, ensure_ascii=False)
        await asyncio.to_thread(_datei_schreiben, datei_pfad, content)
    except OSError as fehler:
        logger.error("[%s] Dateisystem-Fehler fuer %s: %s",
                     JOB_TYPE_ARCHIVIEREN, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_ARCHIVE, f"Dateisystem-Fehler: {str(fehler)}")
    except Exception as fehler:
        logger.error("[%s] Unerwarteter Fehler fuer %s: %s",
                     JOB_TYPE_ARCHIVIEREN, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_ARCHIVE, f"Unerwarteter Fehler bei Archivierung: {str(fehler)}")

    logger.info("[%s] Abschluss archiviert: %s", JOB_TYPE_ARCHIVIEREN, datei_pfad)
    return {"archiveStatus": "DONE"}


def _datei_schreiben(pfad: Path, content: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(content)


def registriere_archive_handler(worker) -> None:
    """Registriert den Archivierungs-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_ARCHIVIEREN,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_archivieren)
