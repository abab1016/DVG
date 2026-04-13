# Sprint 1 — Dokumentation

**Projekt:** DVG — Digitalisierung Eingangsrechnungsbearbeitung  
**Sprint-Zeitraum:** April 2026  
**Team:** Sam Haghighi, Efe Yueksei, Nick Rusna, Abubakar Abdi Tube  
**GitHub:** [GitHub-Repository-URL eintragen]

---

## Ziel des Sprints

Ziel war es, einen funktionierenden Prototyp zu bauen, der zwei Integrationsstile praktisch verbindet:

- **Synchrone Kommunikation** per gRPC: Rechnungsmetadaten speichern und abrufen
- **Asynchrone Kommunikation** per Messaging: Zahlungsaufträge über einen Message Broker übertragen

Am Ende des Sprints sollte ein Client existieren, der beide Bausteine in einem sauberen Ablauf verbindet.

---

## Architekturentscheidungen

| Entscheidung | Begründung |
|---|---|
| **gRPC** für Rechnungsmetadaten | Definierte Schnittstelle per `.proto`, starke Typisierung, gut testbar ohne laufenden Service |
| **RabbitMQ** als Message Broker | Einfacher Einstieg, durable Queues, Management-UI für Debugging, Docker-Image verfügbar |
| **JSON-Dateipersistenz** | Kein Datenbankaufwand für den Prototyp, direkt lesbar und debuggbar |
| **Docker Compose** für Broker | Reproduzierbares Lokal-Setup ohne manuelle Installation |
| **Python** für alle Komponenten | Einheitliche Sprache im Team, schnelle Entwicklung, gute gRPC- und pika-Bibliotheken |

---

## Umgesetzte Komponenten

### Aufgabe 2 — gRPC-Service (`grpc-service/`)

| Datei | Beschreibung |
|---|---|
| `src/proto/invoice.proto` | Service-Definition: `SpeichereRechnungsmetadaten`, `HoleRechnungsmetadaten` |
| `src/server.py` | Server-Implementierung mit Validierung und JSON-Persistenz |
| `src/invoice_pb2.py` / `invoice_pb2_grpc.py` | Generierte Proto-Stubs |
| `tests/test_server.py` | 7 Unit-Tests |

Fehlerbehandlung: `INVALID_ARGUMENT` bei leerer ID, `ALREADY_EXISTS` bei doppelter ID, `NOT_FOUND` beim Abrufen nicht vorhandener Rechnungen.

### Aufgabe 3 — Zahlungssystem (`zahlungssystem/`)

| Datei | Beschreibung |
|---|---|
| `src/consumer.py` | RabbitMQ-Consumer mit Validierung und Status-Logging |

Queue: `zahlungsauftraege` (durable, persistent). Der Consumer validiert alle Pflichtfelder und den Betrag. Ungültige Nachrichten werden per `basic_nack` verworfen. Gültige Zahlungen werden simuliert: Status `RECEIVED` → `PROCESSED` (80 %) oder `FAILED` (20 %). Alle Statusübergänge werden in `Rechnungsdaten/zahlungslog.json` protokolliert.

Fehlerbehandlung: `nack` bei JSON-Fehler, `nack` bei fehlendem Pflichtfeld, `nack` bei ungültigem Betrag (≤ 0), automatischer Reconnect bei Broker-Ausfall.

### Aufgabe 4 — Client (`client/`)

| Datei | Beschreibung |
|---|---|
| `src/ui.py` | Interaktives Menü (Demo-Rechnung, manuelle Eingabe, JSON-Datei) |
| `src/client.py` | Nicht-interaktiver CLI-Einstieg mit `--file`-Flag |
| `src/grpc_client.py` | gRPC-Wrapper mit Fehlerbehandlung für alle Fehlercodes |
| `src/payment_producer.py` | Erstellt Zahlungsauftrag aus Rechnungsdaten und sendet ihn an RabbitMQ |

Der Ablauf: gRPC-Speicherung → bestätigte `invoiceId` übernehmen → Zahlungsauftrag senden. Scheitert die gRPC-Speicherung, wird kein Zahlungsauftrag ausgelöst.

### Aufgabe 5 — Review, Tests und Dokumentation

- Nachbesserungen aus dem Review umgesetzt (siehe Review-Protokoll)
- Testanzahl von 24 auf 27 erweitert
- README aktualisiert
- Sprint-Dokumentation und Review-Protokoll erstellt

---

## Testübersicht

```bash
python -m pytest grpc-service/tests/ client/src/tests/ zahlungssystem/src/tests/ -v
```

**27 Tests** über 4 Testdateien. Kein laufender Service nötig — alle externen Abhängigkeiten (gRPC-Server, RabbitMQ) werden gemockt.

| Testdatei | Anzahl | Abgedeckte Fälle |
|---|---|---|
| `grpc-service/tests/test_server.py` | 7 | Speichern, Datei anlegen, leere ID, Leerzeichen-ID, doppelte ID, Abrufen, nicht gefunden |
| `client/src/tests/test_grpc_client.py` | 6 | Erfolg, Kanal schließen, Server weg, Timeout, ungültige Eingabe, `success=False` |
| `client/src/tests/test_payment_producer.py` | 7 | Auftragsfelder, bestätigte ID, Bruttobetrag, Warteschlange, Persistenz, Verbindung, Verbindungsfehler |
| `zahlungssystem/src/tests/test_consumer.py` | 7 | Bestätigung, Ausgabe, NACK bei JSON-Fehler, NACK fehlendes Feld, NACK negativer Betrag, Eintrag schreiben, Einträge anhängen |

---

## End-to-End-Demo

Der vollständige Ablauf wird durch `demo.sh` automatisiert:

```bash
# Automatischer Demo-Durchlauf (kein Menü):
bash demo.sh --demo

# Interaktives Menü:
bash demo.sh
```

Das Skript:
1. Prüft Voraussetzungen (Python, Docker)
2. Generiert Proto-Stubs falls nötig
3. Startet RabbitMQ (wartet auf Healthcheck)
4. Startet gRPC-Service im Hintergrund
5. Startet Zahlungssystem (Consumer) im Hintergrund
6. Startet Client (Demo-Modus oder interaktiv)
7. Räumt alle Prozesse bei Strg+C auf

**Erwartetes Ergebnis nach einem Durchlauf:**
- `Rechnungsdaten/INV-2026-001.json` — gespeicherte Rechnungsmetadaten
- `Rechnungsdaten/zahlungslog.json` — Eintrag mit Status `BEZAHLT`
- Konsolenausgabe des Consumers mit allen Zahlungsdetails

---

## Bekannte Einschränkungen

Alle offenen Punkte sind technische Schulden, die den Prototyp-Charakter des Sprints widerspiegeln. Keine davon blockiert die Demonstrierbarkeit.

Details im [Review-Protokoll](review_protokoll.md).
