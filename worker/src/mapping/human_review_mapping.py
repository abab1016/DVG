"""Datenvertrag: Korrigierte Human-Review-Daten -> finale Prozessvariablen (Sprint 6).

Nach dem Plausibilitaets-Gateway (validate-ai-extraction -> NEEDS_REVIEW) korrigiert
ein Mensch im User-Task die unsicheren Felder. Dieses Modul fuehrt die korrigierten
Werte mit den urspruenglich AI-extrahierten Prozessvariablen zusammen und gibt die
*finalen* Prozessvariablen zurueck, die der bestehende save-invoice-metadata- (gRPC)
und send-payment-order- (RabbitMQ) Schritt unveraendert weiterverwendet.

Leitgedanken:

1. Die menschliche Korrektur hat IMMER Vorrang vor dem AI-Wert. Felder, die im
   Formular leer bleiben, gelten als "nicht korrigiert" -> der AI-Wert bleibt stehen.

2. invoiceId (technischer Korrelationsschluessel fuer Zeebe-Messages) und
   invoiceNumber (fachliche Rechnungsnummer) muessen nach dem Merge konsistent
   vorhanden sein. Beide werden als nicht-leere Strings sichergestellt; fehlt eines,
   ist das ein fachlicher Fehler (MappingFehler -> BusinessError im Handler), der
   zurueck in die manuelle Bearbeitung fuehrt, statt spaeter den gRPC-Schritt mit
   einer unklaren Meldung scheitern zu lassen. invoiceId selbst ist NICHT
   korrigierbar (read-only) und wird stets aus den Prozessvariablen uebernommen;
   nur die fachliche invoiceNumber darf der Mensch anpassen.

3. Es werden ausschliesslich bekannte, fachlich korrigierbare Felder uebernommen
   (KORRIGIERBARE_FELDER). Unbekannte Schluessel aus dem Formular werden ignoriert,
   damit keine Fremdschluessel in den nachgelagerten gRPC-/Zahlungs-Schritt gelangen
   (grpc_mapping._pruefe_proto_schluessel waere das zweite Sicherheitsnetz).

MappingFehler wird nur bei strukturell ungueltigem Input oder fehlender ID-Konsistenz
geworfen - nicht bei "harmlos leeren" Korrekturen.
"""
from typing import Any, Dict, List, Optional

# Felder, die ein Mensch im Review-Formular korrigieren darf: die fachlichen Felder
# aus dem AI-Datenvertrag (ai_extraction_mapping.AI_PFLICHTFELDER + AI_OPTIONALE_FELDER),
# jedoch BEWUSST OHNE invoiceId. invoiceId ist der technische Korrelationsschluessel
# der Zeebe-Messages und darf mitten im laufenden Prozess nicht ueberschrieben werden -
# er wird stets unveraendert aus den Prozessvariablen uebernommen (siehe finale_id unten).
# Ebenso bewusst KEINE technischen/abgeleiteten Variablen wie channel,
# aiPlausibilityStatus oder confidence.
KORRIGIERBARE_FELDER = [
    "invoiceNumber",
    "supplierName",
    "invoiceDate",
    "amountGross",
    "amountNet",
    "currency",
    "iban",
    "billingAddress",
    "dueDate",
]

# Prozessvariable, unter der das Review-Formular die Korrekturen liefert.
REVIEW_VARIABLE = "humanReviewData"

# Status nach einer abgeschlossenen menschlichen Pruefung. Loest aiPlausibilityStatus
# ("NEEDS_REVIEW") ab, damit ein erneut auswertendes Gateway den Vorgang als erledigt
# erkennt.
STATUS_REVIEWED = "REVIEWED"


class MappingFehler(ValueError):
    """Wird geworfen, wenn die Human-Review-Daten strukturell ungueltig sind
    oder invoiceId/invoiceNumber nach dem Merge nicht konsistent vorliegen."""


def wende_human_review_an(
    variablen: Dict[str, Any],
    korrekturen: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fuehrt korrigierte Human-Review-Daten mit den AI-Prozessvariablen zusammen.

    Args:
        variablen: aktuelle Prozessvariablen (vom AI-Mapping befuellt).
        korrekturen: die im Review-Formular korrigierten Felder als dict, oder None
            wenn keine menschliche Pruefung stattgefunden hat (VALID-Pfad).

    Returns:
        Ein Dict mit den Variablen, die in den Prozess zurueckgeschrieben werden:
        die uebernommenen Korrekturen, die konsistente invoiceId/invoiceNumber sowie
        die Nachvollziehbarkeits-Variablen humanReviewApplied/humanReviewKorrekturen
        (und aiPlausibilityStatus=REVIEWED, falls eine Korrektur erfolgte).

    Raises:
        MappingFehler: bei strukturell ungueltigem Input oder fehlender
            invoiceId/invoiceNumber nach dem Merge.
    """
    _pruefe_struktur(variablen, "variablen")
    if korrekturen is not None:
        _pruefe_struktur(korrekturen, REVIEW_VARIABLE)

    ergebnis: Dict[str, Any] = {}
    uebernommene: List[str] = []

    if korrekturen:
        for feld in KORRIGIERBARE_FELDER:
            if feld in korrekturen and not _ist_leer(korrekturen[feld]):
                ergebnis[feld] = korrekturen[feld]
                if _hat_sich_geaendert(variablen.get(feld), korrekturen[feld]):
                    uebernommene.append(feld)

    # invoiceId / invoiceNumber konsistent halten: korrigierter Wert hat Vorrang,
    # sonst der AI-Wert. Beide muessen am Ende vorhanden sein.
    finale_id = ergebnis.get("invoiceId", variablen.get("invoiceId"))
    finale_nummer = ergebnis.get("invoiceNumber", variablen.get("invoiceNumber"))
    _pruefe_id_konsistenz(finale_id, finale_nummer)
    ergebnis["invoiceId"] = str(finale_id).strip()
    ergebnis["invoiceNumber"] = str(finale_nummer).strip()

    ergebnis["humanReviewApplied"] = korrekturen is not None
    ergebnis["humanReviewKorrekturen"] = uebernommene

    # Eine durchgefuehrte Pruefung loest den NEEDS_REVIEW-Zustand auf.
    if korrekturen is not None:
        ergebnis["aiPlausibilityStatus"] = STATUS_REVIEWED
        ergebnis["aiReviewGruende"] = []

    return ergebnis


def _pruefe_struktur(wert: Any, name: str) -> None:
    if not isinstance(wert, dict):
        raise MappingFehler(
            f"'{name}' muss ein Objekt sein, war: {type(wert).__name__}"
        )


def _pruefe_id_konsistenz(invoice_id: Any, invoice_nummer: Any) -> None:
    fehlend = []
    if _ist_leer(invoice_id):
        fehlend.append("invoiceId")
    if _ist_leer(invoice_nummer):
        fehlend.append("invoiceNumber")
    if fehlend:
        raise MappingFehler(
            "invoiceId und invoiceNumber muessen nach dem Review konsistent "
            f"vorhanden sein - fehlt/leer: {', '.join(fehlend)}"
        )


def _hat_sich_geaendert(alt: Any, neu: Any) -> bool:
    if alt is None:
        return True
    return str(alt).strip() != str(neu).strip()


def _ist_leer(wert: Any) -> bool:
    if wert is None:
        return True
    if isinstance(wert, str) and wert.strip() == "":
        return True
    return False
