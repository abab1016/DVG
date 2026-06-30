"""Zeebe-Job-Handler zum automatischen Auslesen von Rechnungs-PDFs.

Service-Task `extract-pdf-metadata` (Job-Type: `extract-pdf-metadata`).
Aufgaben:
  - Liest das PDF (aus dem fileName-Parameter) aus dem Rechnungsdaten-Ordner.
  - Extrahiert Metadaten (ID, IBAN, Beträge, Rechnungsadresse, Positionen) per pypdf und Regex.
  - Gibt die extrahierten Variablen an Zeebe zurück.
  - Setzt die Variable `pdfSuccess` auf True/False für die Verzweigung im Workflow.
"""
import base64
import logging
import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_PRODUKTIONSWURZEL = Path(__file__).resolve().parent.parent.parent.parent
_ARCHIV_ORDNER = _PRODUKTIONSWURZEL / "Rechnungsdaten"

JOB_TYPE_PDF_AUSLESEN = "extract-pdf-metadata"
JOB_TIMEOUT_MS = 30_000

# Camunda 8 REST-API (v2) fuer Document Handling. Der filepicker legt nur eine
# Dokument-Referenz in der Prozessvariable ab; die eigentlichen Bytes werden
# ueber diesen Endpunkt heruntergeladen. Zeebe-Gateway-REST-Port muss im
# docker-compose nach aussen gemappt sein (Default hier: 8088 -> Container 8080).
CAMUNDA_REST_ADRESSE = os.getenv("CAMUNDA_REST_ADRESSE", "http://localhost:8088")
CAMUNDA_REST_TOKEN = os.getenv("CAMUNDA_REST_TOKEN")  # optional (Bearer), falls Auth aktiv
CAMUNDA_DOC_TIMEOUT_SEK = float(os.getenv("CAMUNDA_DOC_TIMEOUT", "15"))


def _sicherer_dateiname(name: str, fallback: str = "portal_rechnung.pdf") -> str:
    """Reduziert einen Namen auf einen Basisnamen ohne Pfadanteile (Path-Traversal-Schutz)."""
    if not name:
        return fallback
    basis = Path(str(name).replace("\\", "/")).name
    basis = basis.strip()
    if not basis or basis in (".", ".."):
        return fallback
    return basis


def _lade_camunda_dokument(referenz: dict) -> str | None:
    """Laedt ein per filepicker hochgeladenes Dokument ueber die Camunda-REST-API.

    `referenz` ist das vom filepicker erzeugte Objekt mit documentId/storeId/metadata.
    Gibt den lokal gespeicherten Dateinamen zurueck oder None bei Fehler.
    """
    document_id = referenz.get("documentId")
    if not document_id:
        return None

    metadata = referenz.get("metadata") or {}
    roh_name = metadata.get("fileName") or referenz.get("fileName") or f"{document_id}.pdf"
    name = _sicherer_dateiname(roh_name)

    url = f"{CAMUNDA_REST_ADRESSE.rstrip('/')}/v2/documents/{urllib.parse.quote(str(document_id), safe='')}"
    params = {}
    if referenz.get("storeId"):
        params["storeId"] = referenz["storeId"]
    if referenz.get("contentHash"):
        params["contentHash"] = referenz["contentHash"]
    if params:
        url += "?" + urllib.parse.urlencode(params)

    anfrage = urllib.request.Request(url, method="GET")
    anfrage.add_header("Accept", "application/octet-stream")
    if CAMUNDA_REST_TOKEN:
        anfrage.add_header("Authorization", f"Bearer {CAMUNDA_REST_TOKEN}")

    try:
        with urllib.request.urlopen(anfrage, timeout=CAMUNDA_DOC_TIMEOUT_SEK) as antwort:
            daten = antwort.read()
    except Exception as e:
        logger.error("[%s] Dokument-Download fehlgeschlagen (documentId=%s): %s",
                     JOB_TYPE_PDF_AUSLESEN, document_id, e)
        return None

    if not daten:
        logger.warning("[%s] Dokument %s ist leer.", JOB_TYPE_PDF_AUSLESEN, document_id)
        return None

    _ARCHIV_ORDNER.mkdir(parents=True, exist_ok=True)
    ziel = _ARCHIV_ORDNER / name
    ziel.write_bytes(daten)
    logger.info("[%s] Camunda-Dokument heruntergeladen und gespeichert: %s", JOB_TYPE_PDF_AUSLESEN, ziel)
    return name


def speichere_upload(pdf_upload_var: Any) -> str | None:
    """Wertet eine Portal-Filepicker-Variable aus und speichert die PDF auf Disk.

    Oeffentliche API: wird sowohl vom PDF-Auslesen (E-Mail-Pfad) als auch von der
    Archivierung (Portal-Pfad, archive_handler) genutzt, um die hochgeladene
    Original-Rechnung dauerhaft im Rechnungsdaten-Ordner abzulegen.

    Unterstuetzt zwei Formate:
      1. Camunda Document Reference (nativer filepicker, C8 8.6) -> Download via REST-API.
      2. Inline-Base64 (Tests / alternative Clients) -> direktes Dekodieren.

    Gibt den Dateinamen zurueck oder None, wenn kein auswertbares Upload-Objekt vorhanden.
    """
    if not pdf_upload_var:
        return None
    eintrag = pdf_upload_var[0] if isinstance(pdf_upload_var, list) else pdf_upload_var
    if not isinstance(eintrag, dict):
        return None

    # Format 1: Camunda-Dokument-Referenz (filepicker)
    if eintrag.get("documentId"):
        return _lade_camunda_dokument(eintrag)

    # Format 2: Inline-Base64
    content_b64 = eintrag.get("content") or eintrag.get("data") or eintrag.get("fileContent")
    if not content_b64:
        return None
    name = _sicherer_dateiname(eintrag.get("name") or eintrag.get("filename"))
    _ARCHIV_ORDNER.mkdir(parents=True, exist_ok=True)
    ziel = _ARCHIV_ORDNER / name
    ziel.write_bytes(base64.b64decode(content_b64))
    logger.info("[%s] Hochgeladene PDF (Base64) gespeichert: %s", JOB_TYPE_PDF_AUSLESEN, ziel)
    return name


async def handle_pdf_auslesen(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `extract-pdf-metadata`."""
    # Portal-Upload (filepicker) hat Vorrang vor manuellem fileName
    pdf_upload = variablen.get("pdfUpload")
    file_name = variablen.get("fileName", "")
    gespeicherter_name = speichere_upload(pdf_upload)
    if gespeicherter_name:
        file_name = gespeicherter_name

    # Eingangskanal einmal bestimmen: Portal-Upload sonst E-Mail (Default).
    quelle = "PORTAL" if gespeicherter_name else "EMAIL"

    if not file_name:
        logger.warning("[%s] Kein Dateiname angegeben. Überspringe automatische Extraktion.", JOB_TYPE_PDF_AUSLESEN)
        return {"pdfSuccess": False, "errorMessage": "Kein Dateiname angegeben.", "channel": quelle}

    # Pfad zur PDF ermitteln
    pdf_path = _ARCHIV_ORDNER / file_name
    if not pdf_path.exists():
        # Fallback im aktuellen Verzeichnis suchen
        pdf_path = Path(file_name)
        if not pdf_path.exists():
            logger.warning("[%s] PDF-Datei %s nicht gefunden.", JOB_TYPE_PDF_AUSLESEN, file_name)
            return {"pdfSuccess": False, "errorMessage": f"PDF-Datei '{file_name}' wurde nicht gefunden.", "channel": quelle}

    logger.info("[%s] Lese PDF-Metadaten aus: %s", JOB_TYPE_PDF_AUSLESEN, pdf_path)

    try:
        import pypdf
    except ImportError:
        logger.error("[%s] Bibliothek 'pypdf' ist nicht installiert. Automatisches Auslesen nicht möglich.", JOB_TYPE_PDF_AUSLESEN)
        return {"pdfSuccess": False, "errorMessage": "Bibliothek 'pypdf' ist auf dem Worker nicht installiert.", "channel": quelle}

    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        logger.error("[%s] Fehler beim Lesen der PDF-Datei: %s", JOB_TYPE_PDF_AUSLESEN, e)
        return {"pdfSuccess": False, "errorMessage": f"Fehler beim Lesen der PDF: {e}", "channel": quelle}

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
        ergebnis["channel"] = quelle
        return ergebnis

    logger.info("[%s] PDF erfolgreich ausgelesen. ID=%s", JOB_TYPE_PDF_AUSLESEN, daten["invoiceId"])
    daten["pdfSuccess"] = True
    daten["channel"] = quelle
    daten["fileName"] = file_name
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
        if in_items_section and (line_clean.startswith("---") or re.search(r"(?:Netto|Brutto|Total|IBAN):", line_clean, re.IGNORECASE)):
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
        daten["invoiceItems"] = items

    return daten


def registriere_pdf_handler(worker) -> None:
    """Registriert den PDF-Auslesen-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_PDF_AUSLESEN,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_pdf_auslesen)
