# Sprint 6 — AI Agent für Rechnungsinformationen

Dieses Dokument beschreibt die Konzeption, Architektur, Konfiguration und Implementierung des AI-gestützten Rechnungsextraktions-Workflows aus Sprint 6.2.

---

## 1. Übersicht & Zielsetzung

Ziel des Sprint-Abschnitts 6.2 ist die technische Realisierung der automatischen AI-Vorverarbeitung von eingegangenen PDF-Rechnungen. Der manuelle Datenerfassungsschritt (Medienbruch) wird durch eine KI-gestützte Extraktion via n8n und OpenRouter (Gemini LLM) ersetzt. 

```text
E-Mail-Eingang (.pdf) 
→ n8n AI Workflow (OCR + LLM-Extraktion)
→ Plausibilitätsprüfung (Confidence & Betragsabgleich)
→ Wenn VALID: Direktes gRPC-Speichern und RPA-ERP-Erfassung (Dunkelverarbeitung)
→ Wenn NEEDS_REVIEW: Routing an User-Task (Human Review) mit Fehler-Indikation
```

---

## 2. Systemarchitektur & Datenfluss

### 2.1 Logische Komponenten

1. **Camunda 8 (Zeebe)**: Steuert den Gesamtprozess.
2. **pyzeebe Worker**: 
   - Abonniert das Job-Type `run-ai-extraction`.
   - Triggert den n8n-Workflow per HTTP-POST.
   - Evaluiert die Plausibilitätsprüfungen (`pruefe_plausibilitaet()`).
   - Überträgt die transformierten Variablen zurück an Camunda.
3. **n8n AI Engine (Dockerized)**:
   - Führt die PDF-Text-Extraktion aus.
   - Kommuniziert mit OpenRouter zur strukturierten JSON-Generierung.
4. **OpenRouter API**: Schnittstelle zum LLM `google/gemini-2.5-flash`.

### 2.2 Technischer Ablauf im Detail

```mermaid
sequenceFlow
    participant Z as Zeebe (Camunda)
    participant W as pyzeebe Worker
    participant N as n8n Container
    participant LLM as OpenRouter (Gemini)

    Z ->> W: Job: run-ai-extraction (fileName)
    W ->> N: POST /webhook/sprint6-ai-extraction {fileName}
    N ->> N: PDF-Datei von /data/<fileName> auslesen & Text extrahieren
    N ->> LLM: Prompt + PDF-Text übermitteln
    LLM -->> N: Strukturiertes JSON + Confidence-Scores
    N -->> W: Bereinigte JSON-Antwort
    W ->> W: pruefe_plausibilitaet() & Mapping auf Variablen
    W -->> Z: Rückgabe Prozessvariablen (inkl. aiPlausibilityStatus)
```

---

## 3. n8n Einrichtung & Docker-Konfiguration

### 3.1 Docker Integration
n8n wird als containerisierter Dienst innerhalb der bestehenden `docker-compose.yml` gestartet. Der gemeinsame Ordner `Rechnungsdaten/` wird nach `/data` im n8n-Container gemountet:

```yaml
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=Europe/Berlin
    volumes:
      - n8n-data:/home/node/.n8n
      - ./Rechnungsdaten:/data
```

### 3.2 OpenRouter API Key konfigurieren
Der API-Key wird lokal in der `.env`-Datei eingetragen:
```env
OPENROUTER_API_KEY=dein-api-key-von-openrouter
```
n8n greift über die Umgebungsvariablen automatisch auf diesen Key zu (`$env.OPENROUTER_API_KEY`).

### 3.3 Workflow importieren
Der fertige Workflow ist unter [n8n/workflows/sprint6_ai_extraction.json](file:///Users/swe/DVG/DVG/n8n/workflows/sprint6_ai_extraction.json) abgelegt.
1. Öffne das n8n-Dashboard unter [http://localhost:5678](http://localhost:5678).
2. Klicke auf **Workflows** → **Add Workflow** → **Import from File**.
3. Wähle die Datei `sprint6_ai_extraction.json` aus.
4. Aktiviere den Workflow (Schalter oben rechts auf **Active**).

---

## 4. Datenvertrag & Plausibilitätsprüfung

Der Datenvertrag ist in [ai_extraction_mapping.py](file:///Users/swe/DVG/DVG/worker/src/mapping/ai_extraction_mapping.py) fest definiert.

### 4.1 Plausibilitätsregeln (`pruefe_plausibilitaet`)
Eine Extraktion gilt als **VALID**, wenn:
- Alle Pflichtfelder (`invoiceId`, `invoiceNumber`, `supplierName`, `invoiceDate`, `amountGross`, `currency`, `iban`, `billingAddress`) vorhanden und nicht leer sind.
- Die Confidence für jedes Pflichtfeld $\ge 0.85$ ist.
- `amountGross >= amountNet` gilt (falls `amountNet` extrahiert wurde) und beide Werte nicht-negativ sind.
- Die Währung exakt 3 Großbuchstaben entspricht (z. B. `EUR`).

Andernfalls wird der Status auf **NEEDS_REVIEW** gesetzt und die genauen Abweichungen im Feld `aiReviewGruende` gelistet.

### 4.2 Fallback bei technischen Fehlern
Sollte n8n oder die OpenRouter API nicht erreichbar sein, fängt der Worker diesen Fehler ab und gibt automatisch Folgendes zurück:
- `aiPlausibilityStatus = "NEEDS_REVIEW"`
- `aiReviewGruende = "Verbindung zu n8n fehlgeschlagen: [Fehlermeldung]"`

Dadurch ist gewährleistet, dass der Geschäftsprozess bei Systemausfällen niemals stoppt, sondern sicher in den manuellen Human-Review-Pfad übergeht.

---

## 5. Camunda BPMN- & Formular-Anpassungen

### 5.1 BPMN-Modell (`G7_Rechnungsfreigabe_with_AI.bpmn`)
Der Prozess wurde in [G7_Rechnungsfreigabe_with_AI.bpmn](file:///Users/swe/DVG/DVG/BPMN/G7_Rechnungsfreigabe_with_AI.bpmn) neu modelliert und in [deploy_bmpn.py](file:///Users/swe/DVG/DVG/deploy_bmpn.py) als exklusives Deployment registriert.

```text
[StartEvent_Email] 
  ──> Service Task: AI-Extraktion durchführen (run-ai-extraction)
  ──> Exclusive Gateway: Plausibilität ausreichend?
         ├── [Ja]  (aiPlausibilityStatus = "VALID") ──> Merge vor gRPC (Metadaten speichern)
         └── [Nein] (aiPlausibilityStatus = "NEEDS_REVIEW") ──> User Task: Metadaten erfassen
```

### 5.2 Human-Review-Formular (`Metadaten_Erfassung.form`)
Das Formular in [Metadaten_Erfassung.form](file:///Users/swe/DVG/DVG/BPMN/Forms/Metadaten_Erfassung.form) wurde erweitert:
- Am Anfang wird eine gelbe Warnbox mit den Ursachen für den Review (`{{aiReviewGruende}}`) eingeblendet.
- Diese Warnbox wird über die FEEL-Bedingung `=aiPlausibilityStatus != "NEEDS_REVIEW"` ausgeblendet, falls der Prozess über das Portal gestartet wird (keine KI-Fehler).

---

## 6. End-to-End Testanleitung

1. **Umgebung vorbereiten**: Trage deinen OpenRouter API-Key in `.env` ein.
2. **Dienste starten**:
   ```bash
   ./start_all.sh
   ```
3. **n8n Workflow aktivieren**: Importiere und aktiviere die Datei [sprint6_ai_extraction.json](file:///Users/swe/DVG/DVG/n8n/workflows/sprint6_ai_extraction.json) unter [http://localhost:5678](http://localhost:5678).
4. **Happy-Path simulieren**:
   - Führe `python3 auto_email_start.py` aus.
   - Da die standardmäßige Beispielrechnung alle Pflichtfelder enthält und das LLM diese mit hoher Confidence extrahiert, läuft der Prozess vollautomatisch durch:
     - Die Metadaten werden im gRPC-Service gespeichert.
     - Der UiPath RPA-Bot erfasst die Daten (simuliert oder echt).
     - Der Zahlungsauftrag wird per RabbitMQ ausgelöst und archiviert.
5. **Human-Review simulieren**:
   - Editiere künstlich die Confidence-Werte im n8n-Workflow oder übermittle eine unvollständige PDF.
   - Der Camunda-Prozess leitet die Instanz in die Tasklist ([http://localhost:8082](http://localhost:8082)).
   - In dem User-Task "Rechnungsmetadaten erfassen" siehst du die Fehlerursachen (z. B. geringe Confidence) und kannst die Daten manuell freigeben/korrigieren.

---

## 7. Persönliche Lernzusammenfassung (Abu)

### 7.1 Technische Reflexion & Architektur-Erkenntnisse
Die Integration von AI-Agents in deterministische Geschäftsprozesse (wie Camunda BPMN) hat mir verdeutlicht, wie wichtig eine strikte Entkopplung und ein klarer Datenvertrag sind. 
Die Kernherausforderung bei LLMs ist deren stochastische Natur (Nicht-Determinismus). Indem wir n8n als flexible Vorverarbeitungs- und Strukturierungsschicht einsetzen, können wir rohen Text in ein standardisiertes JSON überführen.
Besonders wertvoll war das Konzept des "Confidence-Scores". Anstatt blind auf die LLM-Ausgabe zu vertrauen, zwingt der Prompt das Modell dazu, seine eigene Sicherheit zu bewerten. Unsere im Zeebe-Worker implementierte Plausibilitätslogik fungiert als Gatekeeper: Erst ab einer Confidence von 85 % erlauben wir eine Dunkelverarbeitung. Das ist ein extrem praxistauglicher Hybrid-Ansatz ("Human-in-the-Loop"), der die Prozessgeschwindigkeit maximiert, ohne das Risiko von Fehlbuchungen zu erhöhen.

### 7.2 Hürden & Lösungsansätze
Eine technische Hürde war die Anbindung von OpenRouter innerhalb des Docker-Netzwerks. Da n8n im Container läuft und der Worker auf dem Host, mussten die Netzwerkpfade und Dateizugriffe präzise gemountet werden. Durch das Binden von `./Rechnungsdaten` an `/data` im Container konnte n8n direkt auf die PDFs zugreifen.
Ein weiteres Problem war die Zuverlässigkeit der JSON-Ausgabe des Modells. Obwohl modernere Modelle wie `gemini-2.5-flash` JSON-Modus unterstützen, kam es bei komplexeren Strukturen oder gemischten Währungsformaten zu Abweichungen. Die Implementierung einer separaten Bereinigungsstufe im n8n-Code-Node und die robuste Typkonvertierung im Python-Worker haben dieses Problem erfolgreich gelöst.

### 7.3 Fazit
Die Kombination aus flexiblen Integrationsplattformen (n8n), modernen LLMs (Gemini/OpenRouter) und robusten Workflow-Engines (Camunda) stellt die Zukunft der Hyperautomatisierung dar. Der Prototyp demonstriert eindrucksvoll, wie traditionelle RPA-Ansätze und moderne KI-Lösungen Hand in Hand arbeiten können, um Medienbrüche elegant aufzulösen.
