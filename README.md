# DVG — Digitale Eingangsrechnungsbearbeitung

KI-gestützter Rechnungsfreigabeprozess auf Basis von Camunda 8, Python und Google Gemini (Sprint 1–6).

---

## Schnellstart (5 Schritte)

```
1. Repository klonen
2. plattform.txt setzen  (windows oder mac)
3. .env anlegen          (API-Keys vom Team holen)
4. scripts\install.bat   (einmalig — Dependencies + Docker-Images)
5. scripts\start_all.bat (bei jedem Start)
```

Danach läuft alles — Zeebe, Tasklist, RabbitMQ, n8n, gRPC-Service, Worker.

---

## Architektur

```
Rechnung (PDF)
      │
      ▼
 n8n-Webhook ──► Gemini API
      │               (KI-Extraktion)
      ▼
 Camunda 8 / Zeebe
      │
      ├──► pyzeebe Worker
      │         │
      │    ┌────┴──────────────────┐
      │    │                       │
      │    ▼                       ▼
      │  gRPC-Service          RabbitMQ
      │  (Metadaten)           (Zahlungsauftrag)
      │                            │
      │                            ▼
      │                     Zahlungssystem
      │                     (consumer.py)
      ▼
 Camunda Tasklist
 (Human Review / Freigabe)
```

---

## Voraussetzungen

| Tool | Version | Hinweis |
|------|---------|---------|
| Python | 3.9 oder neuer | Beim Installer: "Add python.exe to PATH" anklicken |
| Docker Desktop | aktuell | Muss vor dem Start laufen |
| Git | aktuell | — |

---

## Schritt 1 — Repository klonen

```bash
git clone <repo-url>
cd DVG
```

---

## Schritt 2 — Plattform setzen

Die Datei `plattform.txt` im Projektordner muss das Betriebssystem enthalten:

**Windows (PowerShell):**
```powershell
"windows" | Out-File plattform.txt -Encoding utf8 -NoNewline
```

**macOS / Linux:**
```bash
echo -n mac > plattform.txt
```

---

## Schritt 3 — `.env` anlegen

Im Projektordner (neben `docker-compose.yml`) eine Datei `.env` erstellen:

```env
# Google Gemini API Key (KI-Extraktion via n8n)
GEMINI_API_KEY=HIER_EINTRAGEN

# UiPath Verbindung (ERP-Bot)
UIPATH_CLIENT_ID=HIER_EINTRAGEN
UIPATH_CLIENT_SECRET=HIER_EINTRAGEN
UIPATH_ORG=HIER_EINTRAGEN
UIPATH_TENANT=DefaultTenant
UIPATH_FOLDER_ID=HIER_EINTRAGEN
UIPATH_QUEUE_NAME=DVG_Rechnungen
```

> Die echten Werte gibt es vom Projektteam. Die `.env` **niemals committen** — sie steht in `.gitignore`.

---

## Schritt 4 — Einmalige Installation

### Windows
```bat
scripts\install.bat
```

### macOS / Linux
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

Das Skript:
- installiert alle Python-Pakete (`worker`, `grpc-service`, `zahlungssystem`)
- lädt die Docker-Images vorab herunter (spart Zeit beim ersten Start)

**Danach einmalig:** gRPC-Stubs generieren — die generierten Dateien sind nicht im Repo:

```bash
# Windows
python -m grpc_tools.protoc -I grpc-service/src/proto --python_out=grpc-service/src --grpc_python_out=grpc-service/src grpc-service/src/proto/invoice.proto

# macOS / Linux
python3 -m grpc_tools.protoc -I grpc-service/src/proto --python_out=grpc-service/src --grpc_python_out=grpc-service/src grpc-service/src/proto/invoice.proto
```

---

## Schritt 5 — System starten

### Windows
```bat
scripts\start_all.bat
```

### macOS / Linux
```bash
./scripts/start_all.sh
```

**Was das Skript automatisch macht:**
1. Startet alle Docker-Container (Zeebe, RabbitMQ, Elasticsearch, Operate, Tasklist, n8n)
2. Wartet bis Zeebe bereit ist
3. Deployed BPMN, Formulare und DMN-Regeln nach Zeebe
4. Öffnet separate Fenster für gRPC-Service, Worker und RabbitMQ-Consumer

**Beim ersten Start:** Docker lädt Images herunter (~5–10 Min).

---

## Schritt 6 — n8n Workflow importieren (einmalig)

Die KI-Extraktion läuft über n8n. Der Workflow muss einmal manuell importiert werden:

1. n8n öffnen: **http://localhost:5678**
2. Oben rechts → **"Import from file"**
3. Datei wählen: `n8n/workflows/sprint6_ai_extraction.json`
4. Workflow aktivieren (Schalter oben rechts auf **"Active"**)

> Ohne aktiven n8n-Workflow schlägt jeder Prozessstart mit `ERR_AI_EXTRACTION` fehl.

---

## BPMN-Fallbacks mit Komponentenausfällen testen

Für jeden technischen BPMN-Schritt mit einem modellierten Error-Boundary gibt
es ein eigenes Ausfallskript. Die Skripte beenden keine realen Dienste, sondern
aktivieren einen Laufzeitmarker. Der laufende Worker erkennt Änderungen ohne
Neustart, führt die im BPMN konfigurierte Anzahl Versuche aus und wechselt dann
in den zugehörigen manuellen Task.

| Komponente | Windows | macOS | Versuche | Manueller Fallback |
| --- | --- | --- | ---: | --- |
| AI / n8n | `scripts\ai_failure.bat` | `./scripts/ai_failure.sh` | 1 | Metadaten manuell erfassen |
| gRPC | `scripts\grpc_failure.bat` | `./scripts/grpc_failure.sh` | 3 | Metadaten manuell speichern |
| UiPath / ERP | `scripts\erp_failure.bat` | `./scripts/erp_failure.sh` | 1 | Rechnung manuell im ERP erfassen |
| RabbitMQ-Zahlung | `scripts\rabbitmq_failure.bat` | `./scripts/rabbitmq_failure.sh` | 3 | Zahlung manuell erfassen |
| Archivierung | `scripts\archive_failure.bat` | `./scripts/archive_failure.sh` | 3 | Rechnung manuell archivieren |

Jedes Skript unterstützt `fail`, `restore` und `status`. Ohne Argument wird ein
kleines Menü angezeigt:

```powershell
scripts\rabbitmq_failure.bat fail
scripts\rabbitmq_failure.bat status
scripts\rabbitmq_failure.bat restore
```

```bash
./scripts/rabbitmq_failure.sh fail
./scripts/rabbitmq_failure.sh status
./scripts/rabbitmq_failure.sh restore
```

Ein aktivierter Ausfall bleibt bestehen, bis dasselbe Skript mit `restore`
aufgerufen wird. Vor einem weiteren Demo-Szenario deshalb den Status prüfen und
nicht mehr benötigte Ausfälle wiederherstellen. Compliance-DMN und
Lieferanten-Rückfrage besitzen im aktuellen BPMN keinen manuellen Fehlerpfad
und werden bewusst nicht über diese Skripte abgeschaltet.

---

## Prozess auslösen

Sobald alles läuft, einen neuen Rechnungsprozess starten:

```bash
# Windows
python scripts/auto_email_start.py

# macOS / Linux
python3 scripts/auto_email_start.py
```

Das Skript generiert eine Test-PDF und schickt die Startnachricht an Zeebe.  
Danach erscheint die Aufgabe "Rechnung prüfen" in der Camunda Tasklist.

---

## Benutzeroberflächen

| Dienst | URL | Login |
|--------|-----|-------|
| **Tasklist** — User Tasks bearbeiten | http://localhost:8082 | demo / demo |
| **Operate** — Prozessinstanzen überwachen | http://localhost:8081 | demo / demo |
| **RabbitMQ** — Warteschlangen einsehen | http://localhost:15672 | admin / admin |
| **n8n** — KI-Workflow verwalten | http://localhost:5678 | — |

---

## System stoppen

### Windows
```bat
scripts\stop_all.bat
```

### macOS / Linux
```bash
./scripts/stop_all.sh
```

---

## Tests

Kein laufendes System erforderlich — alle Services werden gemockt:

```bash
python -m pytest worker/src/tests/ grpc-service/tests/ client/src/tests/ zahlungssystem/src/tests/ -v
```

---

## Ports

| Port | Dienst |
|------|--------|
| 26500 | Zeebe gRPC Gateway |
| 9600 | Zeebe Health (`/actuator/health`) |
| 8081 | Camunda Operate |
| 8082 | Camunda Tasklist |
| 9200 | Elasticsearch |
| 5672 | RabbitMQ AMQP |
| 15672 | RabbitMQ Management |
| 5678 | n8n |
| 50051 | gRPC-Service |
| 8090 | Lieferanten-Simulator (REST) |

---

## Projektstruktur

```
DVG/
├── BPMN/
│   ├── G7_Rechnungsfreigabe_with_AI.bpmn   aktuelles Prozessmodell (Sprint 6)
│   └── Forms/                               Camunda User-Task-Formulare + DMN
├── worker/src/
│   ├── worker.py                            pyzeebe Worker (Einstiegspunkt)
│   └── handlers/                            ein Handler pro Service-Task
├── grpc-service/src/
│   ├── server.py                            Metadaten-Speicher via gRPC
│   └── proto/invoice.proto                  Schnittstellendefinition
├── zahlungssystem/src/
│   └── consumer.py                          RabbitMQ-Consumer (Zahlungsabwicklung)
├── client/src/                              Standalone-Demo Sprint 1 (optional)
├── n8n/workflows/
│   └── sprint6_ai_extraction.json           n8n Workflow für Gemini-Extraktion
├── scripts/                                 Start / Stop / Install / Deploy
├── Rechnungsdaten/                          Laufzeitdaten — nicht im Repo
├── docs/                                    Sprint-Dokumentation
├── docker-compose.yml                       Infrastruktur
├── plattform.txt                            "windows" oder "mac"
└── .env                                     API-Keys — nicht im Repo
```

---

## Häufige Probleme

**Zeebe startet nicht**
```bash
docker compose logs zeebe
# Elasticsearch muss zuerst healthy sein:
docker compose logs elasticsearch
```

**`ModuleNotFoundError: invoice_pb2`**

gRPC-Stubs noch nicht generiert → Befehl aus Schritt 4 ausführen.

**Worker meldet `ERR_AI_EXTRACTION`**

n8n-Workflow ist nicht aktiv → Schritt 6 (Workflow importieren und aktivieren) prüfen.

**Gemini gibt 429 zurück**

Free-Tier-Limit erreicht. Kurz warten (ca. 1 Minute) und erneut versuchen.

**Worker findet `.env` nicht**

Die `.env` muss im Projektordner liegen (neben `docker-compose.yml`), nicht in `worker/`. Der Worker lädt sie beim Start automatisch.
