"""Datenvertrag zwischen der n8n/LLM-AI-Extraktion (Sprint 6) und dem Camunda-Prozess.

Ueberbrueckt zwei Dinge:

1. pruefe_plausibilitaet() bewertet das AI-Extraction-JSON (Pflichtfelder,
   Confidence pro Feld, Betragsplausibilitaet, Waehrungsformat) und liefert
   "VALID" oder "NEEDS_REVIEW" plus eine Liste lesbarer Gruende fuer das
   Human-Review-Formular. Das ist eine fachliche Routing-Entscheidung,
   deshalb wirft die Funktion bei unsicheren/fehlenden Daten bewusst KEINEN
   Fehler (anders als grpc_mapping.py, das von bereits geprueften Daten
   ausgeht).

2. ai_daten_zu_prozessvariablen() bildet das AI-JSON auf dieselben
   Prozessvariablennamen ab, die grpc_mapping.EINGABE_PFLICHT erwartet
   (vorher durch pdf_handler.py befuellt), damit der bestehende
   gRPC-Mapping-Schritt unveraendert weiterlaufen kann.

MappingFehler wird nur bei strukturell ungueltigem Input geworfen (z.B.
ai_daten ist kein Objekt) - das ist ein Integrationsfehler, keine
Plausibilitaetsfrage.
"""
from typing import Any, Dict, List, Optional, Tuple

# Pflichtfelder im AI-Extraction-JSON (Analogie zu den Pflichtfeldern,
# die bisher pdf_handler._extrahiere_daten_aus_text per Regex lieferte).
AI_PFLICHTFELDER = [
    "invoiceId",
    "invoiceNumber",
    "supplierName",
    "invoiceDate",
    "amountGross",
    "currency",
    "iban",
    "billingAddress",
]

# Optionale Felder, die durchgereicht werden, wenn vorhanden.
AI_OPTIONALE_FELDER = ["dueDate", "amountNet"]

CONFIDENCE_SCHWELLE = 0.85

STATUS_VALID = "VALID"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"


class MappingFehler(ValueError):
    """Wird geworfen, wenn das AI-Extraction-JSON strukturell ungueltig ist."""


def pruefe_plausibilitaet(ai_daten: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Bewertet das AI-Extraction-JSON und liefert (status, gruende).

    status ist STATUS_VALID oder STATUS_NEEDS_REVIEW. gruende ist eine Liste
    lesbarer Texte (leer bei VALID), die im Human-Review-Formular angezeigt
    werden koennen.
    """
    _pruefe_struktur(ai_daten)

    confidence = ai_daten.get("confidence", {})
    if not isinstance(confidence, dict):
        confidence = {}

    gruende: List[str] = []

    for feld in AI_PFLICHTFELDER:
        if feld not in ai_daten or _ist_leer(ai_daten[feld]):
            gruende.append(f"Pflichtfeld fehlt: {feld}")
            continue
        feld_confidence = confidence.get(feld)
        if feld_confidence is None:
            gruende.append(f"Keine Confidence-Angabe fuer Pflichtfeld: {feld}")
        elif not isinstance(feld_confidence, (int, float)) or feld_confidence < CONFIDENCE_SCHWELLE:
            gruende.append(
                f"Confidence zu niedrig fuer {feld}: {feld_confidence!r} < {CONFIDENCE_SCHWELLE}"
            )

    gruende.extend(_pruefe_betraege_plausibilitaet(ai_daten))

    if "currency" in ai_daten and not _ist_leer(ai_daten["currency"]):
        waehrung = str(ai_daten["currency"]).strip()
        if len(waehrung) != 3 or not waehrung.isalpha():
            gruende.append(f"Waehrung hat kein gueltiges 3-Buchstaben-Format: {waehrung!r}")

    status = STATUS_NEEDS_REVIEW if gruende else STATUS_VALID
    return status, gruende


def ai_daten_zu_prozessvariablen(ai_daten: Dict[str, Any]) -> Dict[str, Any]:
    """Bildet das AI-Extraction-JSON auf Camunda-Prozessvariablen ab.

    Verwendet dieselben Feldnamen wie grpc_mapping.EINGABE_PFLICHT, damit das
    Ergebnis ohne weitere Umbenennung an variablen_zu_rechnung() weitergegeben
    werden kann. Ergaenzt aiPlausibilityStatus/aiReviewGruende fuer das neue
    Gateway im BPMN-Prozess.
    """
    _pruefe_struktur(ai_daten)

    status, gruende = pruefe_plausibilitaet(ai_daten)

    variablen: Dict[str, Any] = {"channel": "EMAIL"}
    for feld in AI_PFLICHTFELDER + AI_OPTIONALE_FELDER:
        if feld in ai_daten and not _ist_leer(ai_daten[feld]):
            variablen[feld] = ai_daten[feld]

    if ai_daten.get("invoiceItems"):
        variablen["invoiceItems"] = ai_daten["invoiceItems"]

    if not _ist_leer(ai_daten.get("sourceFile")):
        variablen["fileName"] = ai_daten["sourceFile"]

    variablen["aiPlausibilityStatus"] = status
    variablen["aiReviewGruende"] = gruende
    return variablen


def _pruefe_struktur(ai_daten: Any) -> None:
    if not isinstance(ai_daten, dict):
        raise MappingFehler(
            f"AI-Extraction-JSON muss ein Objekt sein, war: {type(ai_daten).__name__}"
        )


def _pruefe_betraege_plausibilitaet(ai_daten: Dict[str, Any]) -> List[str]:
    gruende: List[str] = []
    gross = _zu_float_oder_none(ai_daten.get("amountGross"))
    net = _zu_float_oder_none(ai_daten.get("amountNet"))

    if not _ist_leer(ai_daten.get("amountGross")) and gross is None:
        gruende.append(f"amountGross ist nicht numerisch: {ai_daten.get('amountGross')!r}")
    elif gross is not None and gross < 0:
        gruende.append(f"amountGross ist negativ: {gross}")

    if not _ist_leer(ai_daten.get("amountNet")) and net is None:
        gruende.append(f"amountNet ist nicht numerisch: {ai_daten.get('amountNet')!r}")
    elif net is not None and net < 0:
        gruende.append(f"amountNet ist negativ: {net}")

    if gross is not None and net is not None and gross < net:
        gruende.append(f"amountGross ({gross}) ist kleiner als amountNet ({net})")

    return gruende


def _ist_leer(wert: Any) -> bool:
    if wert is None:
        return True
    if isinstance(wert, str) and wert.strip() == "":
        return True
    return False


def _zu_float_oder_none(wert: Any) -> Optional[float]:
    if wert is None:
        return None
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None
