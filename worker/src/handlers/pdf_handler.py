"""Zeebe-Job-Handler zum automatischen Auslesen von Rechnungs-PDFs.

Service-Task `extract-pdf-metadata` (Job-Type: `extract-pdf-metadata`).
Aufgaben:
  - Liest das PDF (aus dem fileName-Parameter) aus dem Rechnungsdaten-Ordner.
  - Extrahiert Metadaten (ID, IBAN, Beträge, Rechnungsadresse, Positionen) per pypdf und Regex.
  - Gibt die extrahierten Variablen an Zeebe zurück.
  - Setzt die Variable `pdfSuccess` auf True/False für die Verzweigung im Workflow.
"""
import logging
import re
import json
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_PRODUKTIONSWURZEL = Path(__file__).resolve().parent.parent.parent.parent
_ARCHIV_ORDNER = _PRODUKTIONSWURZEL / "Rechnungsdaten"

JOB_TYPE_PDF_AUSLESEN = "extract-pdf-metadata"
JOB_TIMEOUT_MS = 30_000


async def handle_pdf_auslesen(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `extract-pdf-metadata`."""
    file_name = variablen.get("fileName", "")
    if not file_name:
        logger.warning("[%s] Kein Dateiname angegeben. Überspringe automatische Extraktion.", JOB_TYPE_PDF_AUSLESEN)
        return {"pdfSuccess": False, "errorMessage": "Kein Dateiname angegeben.", "channel": "EMAIL"}

    # Pfad zur PDF ermitteln
    pdf_path = _ARCHIV_ORDNER / file_name
    if not pdf_path.exists():
        # Fallback im aktuellen Verzeichnis suchen
        pdf_path = Path(file_name)
        if not pdf_path.exists():
            logger.warning("[%s] PDF-Datei %s nicht gefunden.", JOB_TYPE_PDF_AUSLESEN, file_name)
            return {"pdfSuccess": False, "errorMessage": f"PDF-Datei '{file_name}' wurde nicht gefunden.", "channel": "EMAIL"}

    logger.info("[%s] Lese PDF-Metadaten aus: %s", JOB_TYPE_PDF_AUSLESEN, pdf_path)

    try:
        import pypdf
    except ImportError:
        logger.error("[%s] Bibliothek 'pypdf' ist nicht installiert. Automatisches Auslesen nicht möglich.", JOB_TYPE_PDF_AUSLESEN)
        return {"pdfSuccess": False, "errorMessage": "Bibliothek 'pypdf' ist auf dem Worker nicht installiert.", "channel": "EMAIL"}

    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        logger.error("[%s] Fehler beim Lesen der PDF-Datei: %s", JOB_TYPE_PDF_AUSLESEN, e)
        return {"pdfSuccess": False, "errorMessage": f"Fehler beim Lesen der PDF: {e}", "channel": "EMAIL"}

    # Text-Parsing mit Regex
    daten = _extrahiere_daten_aus_text(text)

    # Pflichtfelder prüfen
    pflichtfelder = ["invoiceId", "invoiceNumber", "supplierName", "invoiceDate", "amountGross", "currency", "iban", "billingAddress"]
    fehlende = [f for f in pflichtfelder if not daten.get(f)]

    if fehlende:
        logger.warning("[%s] Unvollständige PDF-Daten. Fehlende Felder: %s", JOB_TYPE_PDF_AUSLESEN, fehlende)
        # Wir geben die teilweisen Daten zurück, setzen aber pdfSuccess=False für den manuellen Erfassungsschritt
        ergebnis = {"pdfSuccess": False, "errorMessage": f"Unvollständige Extraktion. Fehlende Felder: {', '.join(fehlende)}"}
        ergebnis.update(daten)
        ergebnis["channel"] = "EMAIL"
        return ergebnis

    logger.info("[%s] PDF erfolgreich ausgelesen. ID=%s", JOB_TYPE_PDF_AUSLESEN, daten["invoiceId"])
    daten["pdfSuccess"] = True
    daten["channel"] = "EMAIL"
    return daten


def _extrahiere_daten_aus_text(text: str) -> Dict[str, Any]:
    """Sucht mit regulären Ausdrücken nach Rechnungsmetadaten im Text."""
    daten: Dict[str, Any] = {}

    # Regex Definitionen
    muster = {
        "invoiceId": r"(?:Rechnungs-ID|Invoice-ID|ID):\s*([A-Za-z0-9-]+)",
        "invoiceNumber": r"(?:Rechnungsnummer|Rechnungs-Nr\.|Invoice Number|RE-Nr\.|RE):\s*([A-Za-z0-9-]+)",
        "supplierName": r"(?:Lieferant|Supplier|Verkäufer):\s*([^\n]+)",
        "supplierEmail": r"(?:E-Mail|Email):\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        "invoiceDate": r"(?:Rechnungsdatum|Datum|Date):\s*(\d{4}-\d{2}-\d{2})",
        "dueDate": r"(?:Fälligkeitsdatum|Faelligkeitsdatum|Due Date):\s*(\d{4}-\d{2}-\d{2})",
        "amountGross": r"(?:Brutto|Bruttobetrag|Total Gross|Gross):\s*([\d,.]+)",
        "amountNet": r"(?:Netto|Nettobetrag|Total Net|Net):\s*([\d,.]+)",
        "currency": r"(?:Währung|Waehrung|Currency):\s*([A-Z]{3})",
        "iban": r"(?:IBAN):\s*([A-Z0-9 ]+)",
        "billingAddress": r"(?:Rechnungsadresse|Rechnungs-Adresse|Billing Address):\s*([^\n]+)",
    }

    for key, regex in muster.items():
        match = re.search(regex, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key in ("amountGross", "amountNet"):
                # Konvertiere deutsches/englisches Zahlenformat in Float (z.B. 1.190,50 oder 1190.50)
                try:
                    # Tausenderpunkte entfernen, Komma durch Punkt ersetzen
                    if "," in value and "." in value:
                        # Deutsch: 1.234,56 -> 1234.56
                        if value.rfind(",") > value.rfind("."):
                            value = value.replace(".", "").replace(",", ".")
                        # Englisch: 1,234.56 -> 1234.56
                        else:
                            value = value.replace(",", "")
                    elif "," in value:
                        # Nur Komma vorhanden: 1234,56 -> 1234.56
                        value = value.replace(",", ".")
                    daten[key] = float(value)
                except ValueError:
                    logger.warning("Konnte Betrag '%s' für %s nicht parsen.", value, key)
            elif key == "iban":
                # Leerzeichen aus IBAN entfernen
                daten[key] = value.replace(" ", "")
            else:
                daten[key] = value

    # Positionen auslesen
    items = []
    lines = text.split("\n")
    in_items_section = False
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        # Starte Bereich
        if re.search(r"(?:Positionen|Items|Rechnungspositionen):", line_clean, re.IGNORECASE):
            in_items_section = True
            continue
        # Ende Bereich
        if in_items_section and line_clean.startswith("---") or re.search(r"(?:Netto|Brutto|Total|IBAN):", line_clean, re.IGNORECASE):
            in_items_section = False
            continue

        if in_items_section and line_clean.startswith("-"):
            # Format: - Consulting (Quantity: 2, UnitPrice: 50.00)
            m1 = re.match(r"-\s*(.*?)\s*\(Quantity:\s*([\d.]+),\s*UnitPrice:\s*([\d.]+)\)", line_clean, re.IGNORECASE)
            if m1:
                desc = m1.group(1).strip()
                qty = float(m1.group(2))
                price = float(m1.group(3))
                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unitPrice": price,
                    "totalPrice": round(qty * price, 2)
                })
                continue

            # Format: - Consulting: 2 x 50.00
            m2 = re.match(r"-\s*(.*?):\s*([\d.]+)\s*x\s*([\d.]+)", line_clean, re.IGNORECASE)
            if m2:
                desc = m2.group(1).strip()
                qty = float(m2.group(2))
                price = float(m2.group(3))
                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unitPrice": price,
                    "totalPrice": round(qty * price, 2)
                })
                continue

            # Format: - 2x Consulting (UnitPrice: 50.00) oder ähnlich
            m3 = re.match(r"-\s*([\d.]+)\s*x\s*(.*?)\s*\(UnitPrice:\s*([\d.]+)\)", line_clean, re.IGNORECASE)
            if m3:
                qty = float(m3.group(1))
                desc = m3.group(2).strip()
                price = float(m3.group(3))
                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unitPrice": price,
                    "totalPrice": round(qty * price, 2)
                })
                continue

    if items:
        lines = []
        for item in items:
            lines.append(f"- {item['description']}: {item['quantity']} x {item['unitPrice']} = {item['totalPrice']}")
        daten["invoiceItems"] = "\n".join(lines)

    return daten


def registriere_pdf_handler(worker) -> None:
    """Registriert den PDF-Auslesen-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_PDF_AUSLESEN,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_pdf_auslesen)
