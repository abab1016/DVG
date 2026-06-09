"""Zeebe-Job-Handler zur Simulation oder echten Anbindung der ERP-Erfassung mit einem UiPath-Bot.

Service-Task `Task_UiPathERPErfassung` (Job-Type: `uipath-erp-erfassung`).
Aufgaben:
  - Auslesen der Rechnungsdaten aus den Prozessvariablen.
  - Wenn UiPath-Orchestrator-Umgebungsvariablen gesetzt sind:
      * Echter OAuth-Tokenabruf bei UiPath
      * Hinzufügen des Items in die Orchestrator-Queue (Task 5.4)
      * Polling des Transaktions-Status (Task 5.5)
      * Bei Erfolg: erpEntered = True
      * Bei Fehler oder Timeout: BusinessError(ERR_UIPATH_FAILED) -> Fallback
  - Wenn keine Zugangsdaten gesetzt sind:
      * Simulation des Bot-Laufs
      * Steuerung über `simulateUiPathError`
"""
import logging
import os
import json
import urllib.request
import urllib.parse
import asyncio
from typing import Any, Dict
from pyzeebe.errors import BusinessError

logger = logging.getLogger(__name__)

JOB_TYPE_UIPATH_ERP = "uipath-erp-erfassung"
JOB_TIMEOUT_MS = 300_000  # Erhöhtes Timeout für echten Bot-Lauf (5 Min)

# Fehlercode für das BPMN Error Boundary Event
ERROR_CODE_UIPATH = "ERR_UIPATH_FAILED"


async def handle_uipath_erp_erfassung(**variablen: Any) -> Dict[str, Any]:
    """Service-Task-Handler `uipath-erp-erfassung`."""
    # Dynamisch zur Laufzeit auslesen, da .env erst nach Import geladen wird
    uipath_client_id = os.getenv("UIPATH_CLIENT_ID")
    uipath_client_secret = os.getenv("UIPATH_CLIENT_SECRET")
    uipath_org = os.getenv("UIPATH_ORG")
    uipath_tenant = os.getenv("UIPATH_TENANT", "Default")
    uipath_folder_id = os.getenv("UIPATH_FOLDER_ID")
    uipath_queue_name = os.getenv("UIPATH_QUEUE_NAME")

    invoice_id = variablen.get("invoiceId", "<ohne ID>")
    invoice_number = variablen.get("invoiceNumber", "RE-Unbekannt")
    supplier_name = variablen.get("supplierName", "Unbekannter Lieferant")
    amount_gross = variablen.get("amountGross", 0.0)
    amount_net = variablen.get("amountNet", amount_gross / 1.19)
    
    # Payload für den Bot (Header + Positionen)
    payload = {
        "invoiceNumber": invoice_number,
        "invoiceDate": variablen.get("invoiceDate", ""),
        "supplierName": supplier_name,
        "customerNumber": variablen.get("customerNumber", "K-001"),
        "paymentTerms": variablen.get("dueDate", "14 Tage netto"),
        "comment": "Automatisch erfasst durch UiPath Bot via Camunda 8.",
        "positionDescription": f"Dienstleistungen laut Rechnung {invoice_number}",
        "quantity": "1",
        "unit": "Stk.",
        "unitPriceNet": f"{amount_net:.2f}"
    }

    # Überprüfen, ob die echten UiPath-Umgebungsvariablen definiert und keine Platzhalter sind
    ist_echte_integration = all([
        uipath_client_id,
        uipath_client_secret,
        uipath_org,
        uipath_folder_id,
        uipath_queue_name
    ]) and not any(
        p in (uipath_client_id or "") or p in (uipath_client_secret or "")
        for p in ["dein-oauth-client-id", "dein-oauth-client-secret", "dein-organisationsname"]
    )

    if ist_echte_integration:
        logger.info("[%s] Echte UiPath Orchestrator-Integration aktiviert.", JOB_TYPE_UIPATH_ERP)
        try:
            # 1. OAuth-Token holen
            logger.info("[%s] [Real UiPath] Hole OAuth-Access-Token von cloud.uipath.com...", JOB_TYPE_UIPATH_ERP)
            token = await asyncio.to_thread(_get_uipath_token, uipath_client_id, uipath_client_secret)
            
            # 2. Queue Item hinzufügen (Aufgabe 5.4)
            logger.info("[%s] [Real UiPath] Erzeuge Queue Item in Warteschlange '%s'...", JOB_TYPE_UIPATH_ERP, uipath_queue_name)
            reference = f"Camunda-{invoice_id}"
            item_id = await asyncio.to_thread(
                _add_queue_item,
                token,
                uipath_org,
                uipath_tenant,
                uipath_folder_id,
                uipath_queue_name,
                payload,
                reference
            )
            logger.info("[%s] [Real UiPath] Queue Item erfolgreich erzeugt. ID: %s", JOB_TYPE_UIPATH_ERP, item_id)
            
            # 3. Ergebnis abfragen im Polling-Verfahren (Aufgabe 5.5)
            logger.info("[%s] [Real UiPath] Überwache Bot-Verarbeitungsstatus für Item %s...", JOB_TYPE_UIPATH_ERP, item_id)
            status_ergebnis = await _poll_queue_item_status(token, uipath_org, uipath_tenant, uipath_folder_id, item_id)
            
            if status_ergebnis.get("success"):
                logger.info("[%s] [Real UiPath] Bot-Erfassung erfolgreich abgeschlossen!", JOB_TYPE_UIPATH_ERP)
                return {
                    "erpEntered": True,
                    "uipathStatus": "SUCCESS",
                    "uipathRobotName": status_ergebnis.get("robotName", "UiPath-Cloud-Robot")
                }
            else:
                fehler_details = status_ergebnis.get("error", "Unbekannter Fehler während der Roboter-Ausführung.")
                logger.error("[%s] [Real UiPath] Bot-Ausführung fehlgeschlagen: %s", JOB_TYPE_UIPATH_ERP, fehler_details)
                raise BusinessError(ERROR_CODE_UIPATH, f"UiPath-Bot-Ausführung fehlgeschlagen: {fehler_details}")
                
        except Exception as e:
            if isinstance(e, BusinessError):
                raise
            logger.error("[%s] [Real UiPath] Technischer Fehler bei UiPath-Anbindung: %s", JOB_TYPE_UIPATH_ERP, e)
            raise BusinessError(ERROR_CODE_UIPATH, f"Verbindung zu UiPath-Orchestrator fehlgeschlagen: {str(e)}")
            
    else:
        # SIMULATIONSPFAD (Fallback wenn keine Credentials)
        simulate_error = variablen.get("simulateUiPathError", False)
        logger.info("[%s] Keine UiPath-Credentials gefunden. Führe Simulation aus.", JOB_TYPE_UIPATH_ERP)
        
        logger.info("[%s] [Simulated Bot] Öffne ERP-System: https://anhe0003.github.io/this-and-that/ERP_Rechnungserfassung.html", JOB_TYPE_UIPATH_ERP)
        logger.info("[%s] [Simulated Bot] Fülle Rechnungsnummer: %s", JOB_TYPE_UIPATH_ERP, invoice_number)
        logger.info("[%s] [Simulated Bot] Fülle Lieferantenname: %s", JOB_TYPE_UIPATH_ERP, supplier_name)
        logger.info("[%s] [Simulated Bot] Fülle Einzelpreis Netto: %.2f €", JOB_TYPE_UIPATH_ERP, amount_net)
        logger.info("[%s] [Simulated Bot] Klicke 'Rechnung speichern / aktualisieren'...", JOB_TYPE_UIPATH_ERP)
        
        if simulate_error:
            logger.error("[%s] [Simulated Bot] FEHLER: Rechnung %s erscheint nicht in der Rechnungsliste!", JOB_TYPE_UIPATH_ERP, invoice_number)
            raise BusinessError(
                ERROR_CODE_UIPATH,
                f"UiPath-Bot meldet einen Fehler: ERP-Speicherung fehlgeschlagen für Rechnung {invoice_number}."
            )
            
        logger.info("[%s] ERP-Erfassung per UiPath-Bot erfolgreich abgeschlossen (simuliert).", JOB_TYPE_UIPATH_ERP)
        return {
            "erpEntered": True,
            "uipathStatus": "SUCCESS",
            "uipathRobotName": "UiPath-Bot-Sprint5 (Simuliert)"
        }


# --- Hilfsfunktionen für die echte UiPath Orchestrator API -----------------

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _get_uipath_token(client_id: str, client_secret: str) -> str:
    url = "https://cloud.uipath.com/identity_/connect/token"
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "OR.Queues OR.Queues.Write OR.Queues.Read"
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", USER_AGENT)
    
    with urllib.request.urlopen(req) as res:
        response = json.loads(res.read().decode("utf-8"))
        return response["access_token"]


def _add_queue_item(token: str, org: str, tenant: str, folder_id: str, queue_name: str, payload: dict, reference: str) -> int:
    url = f"https://cloud.uipath.com/{org}/{tenant}/orchestrator_/odata/Queues/UiPathODataSvc.AddQueueItem"
    body = {
        "itemData": {
            "Name": queue_name,
            "Priority": "Normal",
            "SpecificContent": payload,
            "Reference": reference
        }
    }
    data = json.dumps(body).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-UIPATH-OrganizationUnitId", folder_id)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    
    with urllib.request.urlopen(req) as res:
        response = json.loads(res.read().decode("utf-8"))
        return response["Id"]


def _get_queue_item_status(token: str, org: str, tenant: str, folder_id: str, item_id: int) -> dict:
    url = f"https://cloud.uipath.com/{org}/{tenant}/orchestrator_/odata/QueueItems({item_id})"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-UIPATH-OrganizationUnitId", folder_id)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


async def _poll_queue_item_status(token: str, org: str, tenant: str, folder_id: str, item_id: int, max_retries: int = 60) -> dict:
    """Pollt den Status des Queue Items bis es fertig verarbeitet ist (Erfolg/Fehler) oder ein Timeout eintritt."""
    for i in range(max_retries):
        try:
            item = await asyncio.to_thread(_get_queue_item_status, token, org, tenant, folder_id, item_id)
            status = item.get("Status")
            
            logger.info("[Real UiPath] Polling status... Versuch %d/%d. Aktueller Status: %s", i + 1, max_retries, status)
            
            if status == "Successful":
                robot_name = item.get("Robot", {}).get("Name", "Unattended-Robot")
                return {"success": True, "robotName": robot_name}
                
            elif status == "Failed":
                exc = item.get("ProcessingException", {}) or {}
                reason = exc.get("Reason", "Unbekannter Fehler im Bot-Ablauf.")
                return {"success": False, "error": reason}
                
            elif status in ("New", "InProgress"):
                # Weiter warten
                await asyncio.sleep(5)
                
            else:
                return {"success": False, "error": f"Unerwarteter Queue-Item Status: {status}"}
                
        except Exception as e:
            logger.warning("[Real UiPath] Fehler beim Polling: %s. Versuche es in 5 Sekunden erneut...", e)
            await asyncio.sleep(5)
            
    return {"success": False, "error": "Timeout beim Warten auf die Verarbeitung durch den UiPath-Bot."}


def registriere_uipath_handler(worker) -> None:
    """Registriert den UiPath-ERP-Erfassungs-Handler beim pyzeebe-Worker."""
    worker.task(
        task_type=JOB_TYPE_UIPATH_ERP,
        timeout_ms=JOB_TIMEOUT_MS,
    )(handle_uipath_erp_erfassung)
