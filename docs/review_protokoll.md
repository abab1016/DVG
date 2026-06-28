# Review-Protokoll — Sprint 1

**Projekt:** DVG — Digitalisierung Eingangsrechnungsbearbeitung  
**Datum:** April 2026  
**Reviewte Aufgaben:** Aufgabe 2 (gRPC-Service), Aufgabe 3 (Zahlungssystem), Aufgabe 4 (Client)

---

## Bewertung der Anforderungen

### Aufgabe 2 — gRPC-Service für Rechnungsmetadaten

| Anforderung | Status |
|---|---|
| `.proto`-Datei mit Service-Definition | Erfüllt |
| Server-Implementierung | Erfüllt |
| Einfache Persistenz | Erfüllt |
| Tests | Erfüllt |
| Technische Dokumentation | Erfüllt |
| Rechnung speichern (Mindestumfang) | Erfüllt |
| Rechnung anhand `invoiceId` lesen (Mindestumfang) | Erfüllt |
| Fehler bei ungültigen Daten (Mindestumfang) | Erfüllt |
| Fehler bei doppelter `invoiceId` (Mindestumfang) | **Behoben** (war offen) |

### Aufgabe 3 — Zahlungssystem mit Messaging

| Anforderung | Status |
|---|---|
| Lokaler Broker (RabbitMQ via Docker) | Erfüllt |
| Queue-Konzept (durable, persistent) | Erfüllt |
| Consumer für Zahlungsaufträge | Erfüllt |
| Zahlungsverarbeitung als Simulation | Erfüllt |
| Ergebnis-Logging | Erfüllt |
| Tests und Demo | Erfüllt |
| Zahlungsauftrag empfangen (Mindestumfang) | Erfüllt |
| Auftrag validieren (Mindestumfang) | **Behoben** (war offen) |
| „Zahlung verarbeitet" protokollieren (Mindestumfang) | Erfüllt |
| Fehlerfälle sichtbar machen (Mindestumfang) | **Behoben** (war offen) |

### Aufgabe 4 — Client

| Anforderung | Status |
|---|---|
| Client-Eingabe / Demo-Skript | Erfüllt |
| Aufruf des gRPC-Services | Erfüllt |
| Versand des Zahlungsauftrags an den Broker | Erfüllt |
| Sauberer Ablauf mit Statusausgaben | Erfüllt |
| Demo-Szenario | Erfüllt |
| Rechnungsmetadaten speichern (Mindestumfang) | Erfüllt |
| Bestätigte `invoiceId` weiterverwenden (Mindestumfang) | Erfüllt |
| Zahlungsauftrag senden (Mindestumfang) | Erfüllt |
| Erfolgs-/Fehlermeldung ausgeben (Mindestumfang) | Erfüllt |

---

## Im Review behobene Punkte

### 1. Doppelte `invoiceId` wurde nicht abgelehnt
**Problem:** Der gRPC-Server hat eine vorhandene Rechnung stillschweigend überschrieben.  
**Behebung:** In `grpc-service/src/server.py` wird vor dem Schreiben geprüft, ob `{invoiceId}.json` bereits existiert. Falls ja, wird `ALREADY_EXISTS` zurückgegeben.  
**Test:** `test_rechnung_speichern_doppelte_id` in `grpc-service/tests/test_server.py`

### 2. Consumer hatte keine inhaltliche Validierung
**Problem:** Der Consumer hat JSON-Nachrichten verarbeitet, ohne Pflichtfelder oder den Betrag zu prüfen.  
**Behebung:** Neue Funktion `validiere_auftrag()` in `zahlungssystem/src/consumer.py` prüft alle 6 Pflichtfelder (`invoiceId`, `supplierName`, `iban`, `amount`, `currency`, `dueDate`) sowie `amount > 0`. Ungültige Nachrichten werden per `basic_nack(requeue=False)` verworfen.  
**Tests:** `test_verarbeite_zahlung_nack_bei_json_fehler`, `..._nack_bei_fehlendem_feld`, `..._nack_bei_negativem_betrag`

---

## Offene Punkte (technische Schulden für folgende Sprints)

| # | Komponente | Beschreibung | Priorität |
|---|---|---|---|
| 1 | gRPC-Service | Keine Authentifizierung — insecure Channel, keine TLS-Verschlüsselung | Mittel |
| 2 | RabbitMQ | Standardzugangsdaten `guest/guest` im Code hart kodiert | Mittel |
| 3 | Consumer | Zahlungsfehler werden mit 20 % Wahrscheinlichkeit simuliert (`FAILED`), ansonsten `PROCESSED` — kein echter externer Zahlungsanbieter | Niedrig |
| 4 | Consumer | Keine IBAN-Format-Validierung (Prüfziffer, Ländercode) | Niedrig |
| 5 | gRPC-Service | Dateipersistenz ohne Sperrmechanismus — bei parallelen Schreibzugriffen möglich instabil | Niedrig |
| 6 | Allgemein | Keine Datenbankanbindung — JSON-Dateien nicht geeignet für Produktivbetrieb | Hoch (nächster Sprint) |
| 7 | Allgemein | Keine Monitoring-/Observability-Lösung (kein strukturiertes Logging, keine Metriken) | Niedrig |

---

## Fazit

Alle Pflichtanforderungen des Sprints sind erfüllt. Die zwei während des Reviews festgestellten Lücken im Mindestumfang wurden noch im Sprint behoben. Das System ist end-to-end demonstrierbar über `scripts/demo.sh --demo`. Die verbleibenden offenen Punkte sind technische Schulden des Prototyp-Charakters und blockieren die Abgabe nicht.
