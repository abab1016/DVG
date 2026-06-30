"""Zeebe-Job-Handler: Korrigierte Human-Review-Daten anwenden (Sprint 6, KAN-457).

Service-Task `apply-human-review` (Job-Type: `apply-human-review`).
Laeuft auf dem NEEDS_REVIEW-Pfad nach dem Human-Review-User-Task und VOR
save-invoice-metadata / send-payment-order. Aufgaben:
  - Empfaengt die im Review-Formular korrigierten Felder als Prozessvariable
    `humanReviewData` (Objekt {feldname: wert}) oder als JSON-String.
  - Fuehrt diese Korrekturen mit den AI-extrahierten Prozessvariablen zusammen;
    die menschliche Korrektur hat Vorrang (human_review_mapping).
  - Stellt invoiceId/invoiceNumber-Konsistenz sicher und setzt
    aiPlausibilityStatus auf REVIEWED.

Die bestehenden gRPC- und RabbitMQ-Handler bleiben unveraendert und lesen
anschliessend die korrigierten Prozessvariablen.

"""
import json
import logging
from typing import Any, Dict, Optional

from pyzeebe.errors import BusinessError

from mapping.human_review_mapping import (
    REVIEW_VARIABLE,
    MappingFehler,
    wende_human_review_an,
)

logger = logging.getLogger(__name__)

JOB_TYPE_HUMAN_REVIEW = "apply-human-review"
JOB_TIMEOUT_MS = 30_000

ERROR_CODE_HUMAN_REVIEW = "ERR_HUMAN_REVIEW"


async def handle_human_review(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `apply-human-review`.

    Liest die optionale Prozessvariable `humanReviewData` (dict oder JSON-String),
    priorisiert die Korrekturen gegenueber den AI-Daten und gibt die finalen
    Prozessvariablen zurueck.
    """
    invoice_id = variablen.get("invoiceId", "<ohne ID>")
    logger.info("[%s] Job empfangen fuer Rechnung %s", JOB_TYPE_HUMAN_REVIEW, invoice_id)

    korrekturen = _parse_review_daten(variablen.get(REVIEW_VARIABLE))

    try:
        ergebnis = wende_human_review_an(variablen, korrekturen)
    except MappingFehler as fehler:
        logger.error("[%s] Human-Review-Merge fehlgeschlagen fuer %s: %s",
                     JOB_TYPE_HUMAN_REVIEW, invoice_id, fehler)
        raise BusinessError(ERROR_CODE_HUMAN_REVIEW, str(fehler))

    logger.info("[%s] Review angewendet fuer %s: applied=%s, korrigierte Felder=%s",
                JOB_TYPE_HUMAN_REVIEW, invoice_id,
                ergebnis["humanReviewApplied"], ergebnis["humanReviewKorrekturen"])

    return ergebnis


def _parse_review_daten(rohdaten: Any) -> Optional[Dict[str, Any]]:
    """Normalisiert die Review-Eingabe zu einem dict oder None.

    None / leerer String bedeutet "keine menschliche Pruefung" (VALID-Pfad).
    Ein dict wird unveraendert uebernommen, ein JSON-String wird geparst.
    """
    if rohdaten is None:
        return None
    if isinstance(rohdaten, str):
        if rohdaten.strip() == "":
            return None
        try:
            geparst = json.loads(rohdaten)
        except json.JSONDecodeError as fehler:
            raise BusinessError(
                ERROR_CODE_HUMAN_REVIEW,
                f"'{REVIEW_VARIABLE}' ist kein gueltiges JSON: {fehler}",
            )
        if not isinstance(geparst, dict):
            raise BusinessError(
                ERROR_CODE_HUMAN_REVIEW,
                f"'{REVIEW_VARIABLE}' muss ein Objekt sein, war: {type(geparst).__name__}",
            )
        return geparst
    if isinstance(rohdaten, dict):
        return rohdaten
    raise BusinessError(
        ERROR_CODE_HUMAN_REVIEW,
        f"'{REVIEW_VARIABLE}' hat unerwarteten Typ: {type(rohdaten).__name__}",
    )


def registriere_human_review_handler(worker) -> None:
    """Registriert den Human-Review-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_HUMAN_REVIEW,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_human_review)
