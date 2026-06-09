"""Mapping zwischen Zeebe-Prozessvariablen und dem RabbitMQ-Zahlungsauftrag-Schema.

Das Ziel-Schema ist in client/src/payment_producer.py definiert (Sprint 1):
  erstelle_zahlungsauftrag() liest aus dem uebergebenen Dict die Felder
  supplierId, supplierName, iban, amountGross, currency, dueDate (invoiceId
  wird als zweites Argument uebergeben, timestamp automatisch gesetzt).
"""
from typing import Any, Dict

PFLICHTFELDER = [
    "invoiceId",
    "supplierName",
    "iban",
    "currency",
]

OPTIONALE_FELDER = ["supplierId", "dueDate"]

FELD_AMOUNT = "amountGross"


class MappingFehler(ValueError):
    """Wird geworfen, wenn Prozessvariablen nicht zum Zahlungsauftrag-Schema passen."""


def variablen_zu_zahlungsauftrag(variablen: Dict[str, Any]) -> Dict[str, Any]:
    """Konvertiert Zeebe-Prozessvariablen in ein Zahlungsauftrag-Dict.

    Das Ergebnis kann direkt an payment_producer.sende_zahlungsauftrag()
    übergeben werden (die Funktion ruft intern erstelle_zahlungsauftrag() auf
    und published dann an RabbitMQ).

    Wirft MappingFehler bei fehlenden Pflichtfeldern oder ungültigem Betrag.
    """
    fehlende = [
        feld for feld in PFLICHTFELDER
        if feld not in variablen or _ist_leer(variablen[feld])
    ]
    if fehlende:
        raise MappingFehler(f"Fehlende Pflichtfelder: {', '.join(fehlende)}")

    if FELD_AMOUNT not in variablen or variablen[FELD_AMOUNT] is None:
        raise MappingFehler(f"Fehlendes Pflichtfeld: {FELD_AMOUNT}")

    amount = variablen[FELD_AMOUNT]
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise MappingFehler(f"Feld '{FELD_AMOUNT}' muss numerisch sein, war: {amount!r}")

    if amount <= 0:
        raise MappingFehler(f"Betrag muss positiv sein, war: {amount}")

    rechnung = {}
    for feld in PFLICHTFELDER:
        rechnung[feld] = str(variablen[feld]).strip()
    for feld in OPTIONALE_FELDER:
        val = variablen.get(feld)
        rechnung[feld] = str(val).strip() if not _ist_leer(val) else ""
    rechnung[FELD_AMOUNT] = amount

    # billingAddress und items durchreichen
    if "billingAddress" in variablen and not _ist_leer(variablen["billingAddress"]):
        rechnung["billingAddress"] = str(variablen["billingAddress"]).strip()
    if "invoiceItems" in variablen and variablen["invoiceItems"]:
        rechnung["items"] = variablen["invoiceItems"]

    return rechnung


def _ist_leer(wert: Any) -> bool:
    if wert is None:
        return True
    if isinstance(wert, str) and wert.strip() == "":
        return True
    return False