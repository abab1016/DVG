"""pyzeebe-Worker fuer den DVG-Workflow (Sprint 4-6).

Verbindet sich mit Zeebe (Camunda 8) und abonniert alle Service-Task-Job-Types:
  - run-ai-extraction        n8n/Gemini-Extraktion ausfuehren (Sprint 6)
  - apply-human-review       korrigierte Human-Review-Daten zusammenfuehren (Sprint 6, KAN-457)
  - extract-pdf-metadata     Rechnungs-PDF automatisch auslesen
  - save-invoice-metadata    gRPC-Metadaten speichern
  - send-payment-order       RabbitMQ-Zahlungsauftrag senden
  - archive-invoice          Prozessabschluss archivieren
  - send-information-request Rueckfrage an Lieferanten "senden"
  - uipath-erp-erfassung     ERP-Erfassung per RPA-Bot
"""
import asyncio
import logging
import os
import json
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

from pyzeebe import ZeebeWorker, ZeebeClient, create_insecure_channel

from handlers.archive_handler import registriere_archive_handler
from handlers.grpc_handler import registriere_grpc_handler
from handlers.info_request_handler import registriere_info_request_handler
from handlers.payment_handler import registriere_payment_handler
from handlers.pdf_handler import registriere_pdf_handler
from handlers.uipath_handler import registriere_uipath_handler
from handlers.ai_extraction_handler import registriere_ai_extraction_handler
from handlers.human_review_handler import registriere_human_review_handler
from failure_injection import component_failure_exception_handler

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")

_HIER = Path(__file__).resolve().parent
_LOG_DATEI = _HIER.parent / "worker.log"

logger = logging.getLogger("worker")


def _load_env_file() -> None:
    """Lädt Umgebungsvariablen aus einer .env-Datei im Workspace-Wurzelverzeichnis, falls vorhanden."""
    env_path = _HIER.parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
            logger.info("[Env-Loader] Umgebungsvariablen erfolgreich aus .env geladen.")
        except Exception as e:
            logger.warning("[Env-Loader] Fehler beim Laden der .env-Datei: %s", e)


def _logging_konfigurieren() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_LOG_DATEI, encoding="utf-8"),
        ],
    )


# --- REST-API für Lieferanten-Simulation (Postman) ---------------------------

class SupplierResponseHTTPServer(HTTPServer):
    """Custom HTTP Server, der Zeebe-Client und Event-Loop hält."""
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, loop, client):
        super().__init__(server_address, RequestHandlerClass)
        self.loop = loop
        self.client = client


class SupplierResponseHandler(BaseHTTPRequestHandler):
    """HTTP-Request-Handler für die Postman-Schnittstelle."""
    
    def log_message(self, format, *args):
        # logging unterdrücken bzw. über Standard-Logger ausgeben
        logger.info("[REST-Gateway] " + format % args)

    def do_GET(self):
        if self.path.startswith("/api/files/"):
            file_name = self.path[len("/api/files/"):]
            if "/" in file_name or "\\" in file_name or ".." in file_name:
                self.send_response(400)
                self.end_headers()
                return
            
            pdf_path = _HIER.parent.parent / "Rechnungsdaten" / file_name
            if not pdf_path.exists():
                self.send_response(404)
                self.end_headers()
                return
            
            try:
                with open(pdf_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition", f"inline; filename=\"{file_name}\"")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                logger.error("[REST-Gateway] Fehler beim Servieren der PDF-Datei: %s", e)
            return
        
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/supplier/response":
            self.send_response(404)
            self.end_headers()
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": f"Ungültiges JSON: {e}"}).encode('utf-8'))
            return

        invoice_id = data.get("invoiceId")
        comment = data.get("comment", "")
        
        if not invoice_id:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": "Fehlendes Feld: invoiceId"}).encode('utf-8'))
            return

        invoice_id = str(invoice_id).strip()
        comment = str(comment).strip()
        logger.info("[REST-Gateway] Empfangen: Rückmeldung für Rechnung %s (Kommentar: %s)", invoice_id, comment)

        # Message an Zeebe publizieren (Thread-safe über den Main Loop)
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.server.client.publish_message(
                    name="Message_Antwort",
                    correlation_key=invoice_id,
                    variables={"infoResponseComment": comment}
                ),
                self.server.loop
            )
            # Auf Ergebnis warten mit Timeout (10s)
            future.result(timeout=10)
        except Exception as e:
            logger.error("[REST-Gateway] Fehler beim Publizieren der Zeebe-Nachricht: %s", e)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": f"Zeebe-Verbindung fehlgeschlagen: {e}"}).encode('utf-8'))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": True,
            "message": f"Nachricht 'Message_Antwort' für Rechnung {invoice_id} erfolgreich korreliert."
        }).encode('utf-8'))


def _starte_http_server(loop, client) -> HTTPServer:
    """Startet den HTTP-Server in einem Hintergrund-Thread."""
    server_address = ("", 8090)
    httpd = SupplierResponseHTTPServer(server_address, SupplierResponseHandler, loop, client)
    
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    
    logger.info("[REST-Gateway] Lieferanten-Simulator auf Port 8090 gestartet.")
    return httpd


# --- Worker Hauptprogramm ---------------------------------------------------

async def main() -> None:
    _logging_konfigurieren()
    _load_env_file()
    logger.info("Starte Worker, verbinde mit Zeebe: %s", ZEEBE_ADRESSE)

    kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
    worker = ZeebeWorker(
        kanal,
        exception_handler=component_failure_exception_handler,
    )
    client = ZeebeClient(kanal)

    # Registriere alle Job-Handler
    registriere_ai_extraction_handler(worker)
    registriere_human_review_handler(worker)
    registriere_pdf_handler(worker)
    registriere_grpc_handler(worker)
    registriere_payment_handler(worker)
    registriere_archive_handler(worker)
    registriere_info_request_handler(worker)
    registriere_uipath_handler(worker)

    # Startet das REST-Gateway für Postman
    loop = asyncio.get_running_loop()
    _starte_http_server(loop, client)

    logger.info(
        "Worker bereit, abonniere Job-Types: "
        "run-ai-extraction, apply-human-review, extract-pdf-metadata, save-invoice-metadata, "
        "send-payment-order, archive-invoice, send-information-request, uipath-erp-erfassung"
    )
    await worker.work()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker beendet (Strg+C)")
