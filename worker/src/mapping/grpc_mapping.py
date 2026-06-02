"""Mapping zwischen Zeebe-Prozessvariablen und dem gRPC Rechnungsmetadaten-Schema.

Zwei getrennte Verträge werden hier überbrückt:

1. EINGABE — Prozessvariablen, die Camunda an den Worker liefert
   (Scope-Doc Abschnitt 14.1 + Pflichtdaten-Regel 11.1):
     Pflicht:  invoiceId, invoiceNumber, supplierName, invoiceDate,
               amountGross, currency, channel
     Optional: fileName, dueDate, iban, amountNet

2. AUSGABE — das Dict, das an grpc_client.speichere_rechnung() geht.
   speichere_rechnung() ruft invoice_pb2.Rechnungsmetadaten(**rechnung) auf,
   also DARF das Dict ausschließlich die 12 Proto-Feldnamen enthalten
   (grpc-service/src/proto/invoice.proto). Jeder Fremdschlüssel (z.B.
   invoiceNumber, channel) würde dort einen ValueError auslösen.

invoiceNumber und channel sind fachliche Prozessvariablen, haben aber kein
Proto-Feld und werden daher NICHT an den gRPC-Service weitergegeben.
"""
from datetime import datetime, timezone
from typing import Any, Dict

# Eingabe: Pflicht-Prozessvariablen laut Scope 14.1 / Regel 11.1
EINGABE_PFLICHT = [
    "invoiceId",
    "invoiceNumber",
    "supplierName",
    "invoiceDate",
    "currency",
    "channel",
]

# Ausgabe: exakt die 12 Felder aus invoice.proto (message Rechnungsmetadaten)
PROTO_FELDER = [
    "invoiceId",
    "supplierId",
    "supplierName",
    "invoiceDate",
    "dueDate",
    "amountNet",
    "amountGross",
    "currency",
    "iban",
    "status",
    "fileName",
    "createdAt",
]


class MappingFehler(ValueError):
    """Wird geworfen, wenn Prozessvariablen nicht zum Rechnungsmetadaten-Schema passen."""


def variablen_zu_rechnung(variablen: Dict[str, Any]) -> Dict[str, Any]:
    """Konvertiert Zeebe-Prozessvariablen in ein Proto-konformes Rechnungs-Dict.

    Validiert die Pflicht-Eingaben (Scope 14.1) und liefert ein Dict, dessen
    Schlüssel eine Teilmenge der 12 Proto-Felder sind, sodass
    invoice_pb2.Rechnungsmetadaten(**ergebnis) nicht fehlschlägt.
    """
    # 1. Eingabe-Pflichtfelder prüfen
    fehlende = [
        feld for feld in EINGABE_PFLICHT
        if feld not in variablen or _ist_leer(variablen[feld])
    ]
    if fehlende:
        raise MappingFehler(f"Fehlende Pflichtfelder: {', '.join(fehlende)}")

    if "amountGross" not in variablen or variablen["amountGross"] is None:
        raise MappingFehler("Fehlendes Pflichtfeld: amountGross")

    amount_gross = _zu_float(variablen["amountGross"], "amountGross")

    # 2. Proto-Dict aufbauen — NUR Proto-Feldnamen
    rechnung: Dict[str, Any] = {
        "invoiceId": str(variablen["invoiceId"]).strip(),
        "supplierName": str(variablen["supplierName"]).strip(),
        "invoiceDate": str(variablen["invoiceDate"]).strip(),
        "currency": str(variablen["currency"]).strip(),
        "amountGross": amount_gross,
        # abgeleitet / Defaults
        "supplierId": _supplier_id_aus_name(str(variablen["supplierName"]).strip()),
        "status": "OPEN",
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    # optionale Proto-Felder aus Prozessvariablen
    for opt in ("fileName", "dueDate", "iban"):
        val = variablen.get(opt)
        rechnung[opt] = str(val).strip() if not _ist_leer(val) else ""

    # amountNet: aus Prozessvariablen oder aus Brutto abgeleitet (/1.19)
    val_net = variablen.get("amountNet")
    if val_net is not None and not _ist_leer(val_net):
        rechnung["amountNet"] = _zu_float(val_net, "amountNet")
    else:
        rechnung["amountNet"] = round(amount_gross / 1.19, 2)

    _pruefe_betraege(rechnung)
    _pruefe_proto_schluessel(rechnung)
    return rechnung


def _zu_float(rohwert: Any, feld: str) -> float:
    try:
        wert = float(rohwert)
    except (TypeError, ValueError):
        raise MappingFehler(f"Feld '{feld}' muss numerisch sein, war: {rohwert!r}")
    if wert != wert or wert in (float("inf"), float("-inf")):  # NaN / Inf
        raise MappingFehler(f"Feld '{feld}' ist kein gueltiger Betrag: {rohwert!r}")
    return wert


def _supplier_id_aus_name(name: str) -> str:
    prefix = "SUP-"
    rest = name.upper()
    for src, dst in [("Ä", "AE"), ("Ö", "OE"), ("Ü", "UE"), ("ß", "SS"), (" ", "-")]:
        rest = rest.replace(src, dst)
    rest = "".join(c for c in rest if c.isalnum() or c == "-")
    return (prefix + rest)[:24] if rest else "SUP-UNKNOWN"


def _ist_leer(wert: Any) -> bool:
    if wert is None:
        return True
    if isinstance(wert, str) and wert.strip() == "":
        return True
    return False


def _pruefe_betraege(rechnung: Dict[str, Any]) -> None:
    net = rechnung["amountNet"]
    gross = rechnung["amountGross"]
    if net < 0 or gross < 0:
        raise MappingFehler("Betraege duerfen nicht negativ sein")
    if gross < net:
        raise MappingFehler(
            f"amountGross ({gross}) darf nicht kleiner sein als amountNet ({net})"
        )


def _pruefe_proto_schluessel(rechnung: Dict[str, Any]) -> None:
    """Sicherheitsnetz: keine Fremdschluessel im gRPC-Dict.

    invoice_pb2.Rechnungsmetadaten(**rechnung) wuerde bei einem unbekannten
    Schluessel mit ValueError abbrechen — hier fangen wir das frueh und mit
    klarer Meldung ab.
    """
    fremd = [k for k in rechnung if k not in PROTO_FELDER]
    if fremd:
        raise MappingFehler(
            f"Interner Mapping-Fehler: Nicht-Proto-Felder im gRPC-Dict: {', '.join(fremd)}"
        )
