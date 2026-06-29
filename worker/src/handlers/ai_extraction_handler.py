"""Zeebe-Job-Handler zur Durchführung der AI-Extraktion über n8n.

Registriert den Job-Type `run-ai-extraction`.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict

from pyzeebe.errors import BusinessError

from failure_injection import raise_if_failure_enabled
from mapping.ai_extraction_mapping import ai_daten_zu_prozessvariablen

logger = logging.getLogger(__name__)

JOB_TYPE_AI_EXTRACTION = "run-ai-extraction"
JOB_TIMEOUT_MS = 60_000  # n8n & LLM-Aufruf kann etwas dauern

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/sprint6-ai-extraction"

# BPMN-Error-Code — muss mit dem Error Boundary Event am Service-Task
# "run-ai-extraction" im BPMN (Error_AI_ID, errorCode "ERR_AI_EXTRACTION")
# übereinstimmen. Boundary führt zur User-Task "Metadaten erfassen".
ERROR_CODE_AI = "ERR_AI_EXTRACTION"


async def handle_ai_extraction(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `run-ai-extraction`."""
    file_name = variablen.get("fileName", "")
    if not file_name:
        logger.warning("[%s] Kein Dateiname angegeben.", JOB_TYPE_AI_EXTRACTION)
        raise BusinessError(ERROR_CODE_AI, "Kein Dateiname in Prozessvariablen angegeben.")

    raise_if_failure_enabled("ai")

    logger.info("[%s] Starte AI-Extraktion für Datei: %s", JOB_TYPE_AI_EXTRACTION, file_name)

    payload = {"fileName": file_name}
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(N8N_WEBHOOK_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        # Führe den HTTP-Call aus
        # Da dies blockierend sein kann, führen wir es im default executor aus (was asyncio.to_thread macht)
        # Aber da wir uns in einer async-Methode befinden, ist ein asynchroner Wrapper gut.
        import asyncio
        
        def make_request():
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read().decode("utf-8")

        response_body = await asyncio.to_thread(make_request)
        response_json = json.loads(response_body)
        
        if isinstance(response_json, list) and len(response_json) > 0:
            response_json = response_json[0]
            
        logger.info("[%s] AI-Extraktion erfolgreich von n8n zurückerhalten.", JOB_TYPE_AI_EXTRACTION)
        
        # Mappe die AI-Daten auf die Prozessvariablen
        prozess_variablen = ai_daten_zu_prozessvariablen(response_json)
        return prozess_variablen

    except urllib.error.URLError as e:
        logger.error("[%s] n8n-Verbindungsfehler für %s: %s", JOB_TYPE_AI_EXTRACTION, file_name, e)
        raise BusinessError(ERROR_CODE_AI, f"Verbindung zu n8n fehlgeschlagen: {e.reason}")
    except Exception as e:
        logger.error("[%s] Unerwarteter Fehler bei AI-Extraktion für %s: %s", JOB_TYPE_AI_EXTRACTION, file_name, e)
        raise BusinessError(ERROR_CODE_AI, f"Technischer Fehler bei AI-Extraktion: {str(e)}")


def registriere_ai_extraction_handler(worker) -> None:
    """Registriert den AI-Extraktion-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_AI_EXTRACTION,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_ai_extraction)
