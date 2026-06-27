"""Mapping und Validierung für AI-extrahierte Rechnungsdaten (n8n/LLM).

Setzt die Anforderungen aus Sprint 6 Vorgang 4 um (Datenvertrag zwischen n8n und Camunda).
"""
import json
import re
from typing import Any, Dict, List, Tuple

# Pflichtfelder laut Datenvertrag
PFLICHTFELDER = [
    "invoiceId",
    "invoiceNumber",
    "supplierName",
    "invoiceDate",
    "amountGross",
    "currency",
    "iban",
    "billingAddress",
]


class MappingFehler(ValueError):
    """Wird geworfen, wenn die AI-Ausgabe strukturell beschädigt ist."""
    pass


def pruefe_plausibilitaet(daten: Dict[str, Any], confidence_schwelle: float = 0.85) -> Tuple[str, List[str]]:
    """Prüft die Plausibilität der AI-extrahierten Daten.

    Regeln:
    1. Alle Pflichtfelder müssen vorhanden und nicht leer sein.
    2. Für jedes Pflichtfeld muss ein Confidence-Wert vorhanden und >= confidence_schwelle sein.
    3. Beträge (amountGross, amountNet falls vorhanden) müssen numerisch, nicht negativ und amountGross >= amountNet sein.
    4. Die Währung (currency) muss ein gültiges 3-Buchstaben-Format sein (z.B. EUR).
    """
    if not isinstance(daten, dict):
        raise MappingFehler("Die Eingabedaten müssen ein JSON-Objekt (Dict) sein.")

    reasons: List[str] = []

    # 1. Pflichtfelder vorhanden und nicht leer prüfen
    for feld in PFLICHTFELDER:
        wert = daten.get(feld)
        if wert is None or (isinstance(wert, str) and not wert.strip()):
            reasons.append(f"Pflichtfeld '{feld}' fehlt oder ist leer.")
            continue

        # 2. Confidence prüfen (nur wenn das Feld überhaupt vorhanden ist)
        confidence_dict = daten.get("confidence")
        if not isinstance(confidence_dict, dict):
            reasons.append(f"Confidence-Objekt fehlt oder ist kein Dictionary.")
            # Falls kein dict da ist, werten wir alle als fehlende confidence
            for f in PFLICHTFELDER:
                reasons.append(f"Confidence für Feld '{f}' fehlt.")
            break

        conf_value = confidence_dict.get(feld)
        if conf_value is None:
            reasons.append(f"Confidence für Feld '{feld}' fehlt.")
        else:
            try:
                conf_float = float(conf_value)
                if conf_float < confidence_schwelle:
                    reasons.append(f"Confidence für Feld '{feld}' ({conf_float:.2f}) liegt unter der Schwelle ({confidence_schwelle:.2f}).")
            except (ValueError, TypeError):
                reasons.append(f"Confidence für Feld '{feld}' ist kein gültiger Float-Wert: {conf_value!r}.")

    # 3. Beträge prüfen
    amount_gross_raw = daten.get("amountGross")
    amount_gross = None
    if amount_gross_raw is not None and amount_gross_raw != "":
        try:
            amount_gross = float(amount_gross_raw)
            if amount_gross < 0:
                reasons.append("amountGross darf nicht negativ sein.")
            if amount_gross != amount_gross or amount_gross in (float("inf"), float("-inf")):
                reasons.append("amountGross ist kein gültiger Float-Wert.")
                amount_gross = None
        except (ValueError, TypeError):
            reasons.append(f"amountGross ist nicht numerisch: {amount_gross_raw!r}.")

    amount_net_raw = daten.get("amountNet")
    amount_net = None
    if amount_net_raw is not None and amount_net_raw != "":
        try:
            amount_net = float(amount_net_raw)
            if amount_net < 0:
                reasons.append("amountNet darf nicht negativ sein.")
            if amount_net != amount_net or amount_net in (float("inf"), float("-inf")):
                reasons.append("amountNet ist kein gültiger Float-Wert.")
                amount_net = None
        except (ValueError, TypeError):
            reasons.append(f"amountNet ist nicht numerisch: {amount_net_raw!r}.")

    if amount_gross is not None and amount_net is not None:
        if amount_gross < amount_net:
            reasons.append(f"amountGross ({amount_gross}) darf nicht kleiner sein als amountNet ({amount_net}).")

    # 4. Währung prüfen
    currency = daten.get("currency")
    if currency:
        if not isinstance(currency, str) or not re.match(r"^[A-Z]{3}$", currency):
            reasons.append(f"Währung '{currency}' entspricht nicht dem 3-Buchstaben-ISO-Format (z.B. EUR).")

    # Ergebnis bestimmen
    status = "NEEDS_REVIEW" if reasons else "VALID"
    return status, reasons


def ai_daten_zu_prozessvariablen(daten: Dict[str, Any]) -> Dict[str, Any]:
    """Transformiert extrahierte AI-Daten in Camunda-Prozessvariablen.

    Führt die Plausibilitätsprüfung aus und setzt `aiPlausibilityStatus` und `aiReviewGruende`.
    """
    if not isinstance(daten, dict):
        raise MappingFehler("Die Eingabedaten müssen ein JSON-Objekt (Dict) sein.")

    status, reasons = pruefe_plausibilitaet(daten)

    # Basisvariablen kopieren
    prozess_variablen = {}
    for key, value in daten.items():
        if key != "confidence":
            prozess_variablen[key] = value

    # Zusätzliche Variablen
    prozess_variablen["channel"] = "EMAIL"
    prozess_variablen["fileName"] = daten.get("sourceFile") or ""
    prozess_variablen["aiPlausibilityStatus"] = status
    prozess_variablen["aiReviewGruende"] = ", ".join(reasons) if reasons else ""

    # invoiceItems normalisieren: dynamiclist in Camunda Forms erwartet ein Array
    raw_items = prozess_variablen.get("invoiceItems", [])
    if isinstance(raw_items, str):
        try:
            parsed = json.loads(raw_items)
            if isinstance(parsed, list):
                prozess_variablen["invoiceItems"] = parsed
            else:
                prozess_variablen["invoiceItems"] = []
        except Exception:
            prozess_variablen["invoiceItems"] = []
    elif not isinstance(raw_items, list):
        prozess_variablen["invoiceItems"] = []

    return prozess_variablen
