# Fehlerfälle und Grenzen (Sprint 6, KAN-459)

Dieses Dokument füllt Abschnitt 14 der Sprint-6-Doku-Struktur
([`sprint6_phase1_scope_doku_demoziel.md`](sprint6_phase1_scope_doku_demoziel.md),
Zeile 325) aus. Es beschreibt, wie der Worker mit Fehlern umgeht, ordnet jeden
Service-Task einer Fehlerklasse zu und benennt die bewussten Grenzen der aktuellen
Umsetzung. Grundlage ist der Code in `worker/src/handlers/` und `worker/src/mapping/`.

## 1. Fehlermodell: drei Reaktionsarten

Der Worker unterscheidet drei Arten, auf eine "nicht erwartete" Eingabe zu reagieren.
Die Wahl der Reaktion ist kein Implementierungsdetail, sondern eine fachliche
Entscheidung: Sie legt fest, ob am Ende ein Mensch, ein Retry oder ein Incident
zuständig ist.

| Reaktion | Auslöser | Technik | Wirkung im BPMN |
| --- | --- | --- | --- |
| **Fachlicher Fehler** | Daten sind dauerhaft nicht verarbeitbar (Duplikat, ungültige/fehlende Pflichtdaten) | `raise BusinessError(<ERR_CODE>, msg)` | Error Boundary Event am Service-Task → User-Task zur manuellen Bearbeitung |
| **Transienter Fehler** | Gegenstelle kurzzeitig weg (Netzwerk, Broker, gRPC-Server) | Exception wird *durchgereicht* (`raise`) | Zeebe-Retry; nach Aufbrauchen der Retries → **Incident** in Operate |
| **Routing-Entscheidung** | Daten unsicher/unvollständig, aber kein Fehler | Variable zurückgeben (`pdfSuccess`, `aiPlausibilityStatus`) | Exklusives Gateway verzweigt (z. B. in Human Review) — **kein** Incident |

Der entscheidende Unterschied zwischen den ersten beiden Zeilen: Ein `BusinessError`
trägt einen **Error-Code**, den das BPMN über ein Error Boundary Event abfängt und in
einen menschlichen Korrekturpfad lenkt. Eine *durchgereichte* Exception trägt keinen
solchen Code, läuft in den Zeebe-Retry und endet — wenn sie bleibt — als Incident,
den ein Operator in Camunda Operate sieht. Ein nicht erreichbarer gRPC-Server soll
sich von selbst erholen (Retry); eine doppelt eingereichte Rechnung nicht — sie
braucht einen Menschen.

Die dritte Zeile ist die wichtigste fachliche Feinheit aus Sprint 6: Eine unsichere
KI-Extraktion ist **kein Fehler**. Sie erzeugt keinen Incident, sondern lenkt den
Prozess über ein Gateway in den Human Review (siehe Abschnitt 3).

## 2. Error-Codes und Routing-Variablen im Überblick

| Code / Variable | Service-Task (Job-Type) | Klasse | Quelle |
| --- | --- | --- | --- |
| `ERR_AI_EXTRACTION` | `validate-ai-extraction` | fachlich | `handlers/ai_extraction_handler.py` |
| `ERR_HUMAN_REVIEW` | `apply-human-review` | fachlich | `handlers/human_review_handler.py` |
| `ERR_GRPC` | `save-invoice-metadata` | fachlich | `handlers/grpc_handler.py` |
| `ERR_RABBITMQ` | `send-payment-order` | fachlich | `handlers/payment_handler.py` |
| `ERR_UIPATH_FAILED` | `uipath-erp-erfassung` | fachlich | `handlers/uipath_handler.py` |
| `ERR_INFO_REQUEST` | `send-information-request` | fachlich (Safety-Net, ohne Boundary) | `handlers/info_request_handler.py` |
| `ERR_ARCHIVE` | `archive-invoice` | fachlich (Safety-Net, ohne Boundary) | `handlers/archive_handler.py` |
| `pdfSuccess` (true/false) | `extract-pdf-metadata` | Routing | `handlers/pdf_handler.py` |
| `aiPlausibilityStatus` (`VALID`/`NEEDS_REVIEW`/`REVIEWED`) | `validate-ai-extraction`, `apply-human-review` | Routing | `mapping/ai_extraction_mapping.py`, `mapping/human_review_mapping.py` |

"Safety-Net, ohne Boundary": Diese Tasks haben im BPMN bewusst **keine** Error
Boundary, weil an ihrer Stelle keine fachlichen Fehler mehr erwartet werden. Ein
trotzdem geworfener `BusinessError` wird daher nicht abgefangen und erzeugt einen
Incident — die richtige, sichtbare Reaktion auf einen Zustand, der nicht hätte
eintreten dürfen.

## 3. Sonderfall NEEDS_REVIEW und der Human-Review-Merge (KAN-457)

Die Plausibilitätsprüfung (`mapping/ai_extraction_mapping.pruefe_plausibilitaet`)
liefert bei fehlenden Pflichtfeldern, zu niedriger Confidence (< 0.85), unplausiblen
Beträgen oder ungültigem Währungsformat **keinen** Fehler, sondern
`aiPlausibilityStatus = "NEEDS_REVIEW"` plus eine Liste lesbarer Gründe
(`aiReviewGruende`). Das Gateway leitet daraufhin in den Human-Review-User-Task
(Scope-Szenario 8.2).

Nach der Korrektur durch den Sachbearbeiter führt der Service-Task
`apply-human-review` (`handlers/human_review_handler.py`,
`mapping/human_review_mapping.py`) die korrigierten Werte mit den AI-Daten zusammen.
Dabei gelten drei Regeln, die direkt aus der Fehler-Perspektive motiviert sind:

1. **Korrektur hat Vorrang.** Ein im Formular gesetztes Feld überschreibt den
   AI-Wert; ein leer gelassenes Feld lässt den AI-Wert stehen. Damit kann eine
   menschliche Korrektur einen unsicheren KI-Wert nicht versehentlich durch "leer"
   ersetzen. So wird die Scope-Anforderung 8.2 erfüllt — die korrigierten Daten
   werden *tatsächlich weiterverwendet*, nicht nur angezeigt.
2. **invoiceId/invoiceNumber-Konsistenz.** Fehlt nach dem Merge eine der beiden IDs,
   wirft der Schritt `ERR_HUMAN_REVIEW` und schickt den Vorgang zurück in die
   manuelle Bearbeitung — statt den Fehler in den nachgelagerten gRPC-Schritt
   durchsickern zu lassen, wo er nur eine unklare Meldung erzeugen würde.
   invoiceId ist der technische Korrelationsschlüssel der Zeebe-Messages,
   invoiceNumber die fachliche Rechnungsnummer; beide müssen erhalten bleiben.
3. **Keine Fremdschlüssel.** Es werden nur bekannte, fachlich korrigierbare Felder
   übernommen (`KORRIGIERBARE_FELDER`). Unbekannte Formularschlüssel werden ignoriert,
   damit sie nicht als Prozessvariablen in den gRPC-Schritt gelangen
   (`grpc_mapping._pruefe_proto_schluessel` ist das zweite Sicherheitsnetz).
   `invoiceId` steht bewusst **nicht** in `KORRIGIERBARE_FELDER`: Der technische
   Korrelationsschlüssel ist read-only und wird stets aus den Prozessvariablen
   übernommen, sodass ein menschlicher Tippfehler die laufende Zeebe-Korrelation
   nicht zerstören kann. Nur `invoiceNumber` ist fachlich korrigierbar.

Nach erfolgreicher Prüfung setzt der Schritt `aiPlausibilityStatus = "REVIEWED"`,
sodass der Prozess wie im Happy Path weiterläuft.

## 4. Fehlerfälle je Service-Task

### 4.1 `extract-pdf-metadata` — PDF nicht lesbar / Pflichtfeld fehlt
`handlers/pdf_handler.py` wirft **keinen** `BusinessError`, sondern signalisiert
Probleme über `pdfSuccess = False` und `errorMessage`:

- Datei nicht gefunden, `pypdf` nicht installiert, PDF nicht parsebar → `pdfSuccess=False`.
- Pflichtfelder nach Regex-Extraktion unvollständig → `pdfSuccess=False`, die
  Teildaten werden trotzdem zurückgegeben.

Das Gateway verzweigt auf `pdfSuccess` in die manuelle Erfassung. Bewusste
Entscheidung: Eine unlesbare PDF ist ein erwarteter Normalfall der Eingangspost und
kein Incident.

### 4.2 `validate-ai-extraction` — LLM-Ausgabe unbrauchbar
`handlers/ai_extraction_handler.py`:

- `aiExtractionData` fehlt, ist kein gültiges JSON oder hat einen falschen Typ
  → `ERR_AI_EXTRACTION` (fachlich, Boundary). Das ist ein *Integrations*fehler im
  Datenvertrag, kein Plausibilitätsproblem.
- Inhaltlich unsichere/unvollständige Daten → `NEEDS_REVIEW` (Routing, siehe Abschnitt 3).

### 4.3 `apply-human-review` — Korrektur unbrauchbar
`handlers/human_review_handler.py`:

- `humanReviewData` ist kein gültiges JSON/Objekt → `ERR_HUMAN_REVIEW`.
- invoiceId/invoiceNumber nach Merge inkonsistent → `ERR_HUMAN_REVIEW`.
- Keine `humanReviewData` vorhanden (Happy Path) → Pass-through ohne Statusänderung.

### 4.4 `save-invoice-metadata` — gRPC-Service
`handlers/grpc_handler.py` trennt fachliche und transiente gRPC-Fehler sauber:

- Mapping-Fehler (Pflichtdaten fehlen, Betrag nicht numerisch) → `ERR_GRPC` (fachlich).
- gRPC `INVALID_ARGUMENT` / `ALREADY_EXISTS` (Duplikat) / `NOT_FOUND` → `ERR_GRPC` (fachlich).
- Service liefert `success=False` (`RuntimeError`) → `ERR_GRPC` (fachlich).
- **Jeder andere** `grpc.RpcError` (z. B. `UNAVAILABLE`, Server nicht erreichbar)
  → wird durchgereicht → Zeebe-Retry → Incident. Das ist der Fall "gRPC-Service
  nicht erreichbar" aus Scope 8.3.

### 4.5 `send-payment-order` — RabbitMQ
`handlers/payment_handler.py`:

- Mapping-Fehler (fehlende Pflichtdaten, Betrag ≤ 0) → `ERR_RABBITMQ` (fachlich).
- `AMQPConnectionError` / `AMQPError` (Broker nicht erreichbar) → durchgereicht →
  Retry → Incident. Das ist der Fall "RabbitMQ nicht erreichbar" aus Scope 8.3.

Der Zahlungsauftrag verwendet konsistent `amountGross` als Zahlbetrag
(`mapping/payment_mapping.FELD_AMOUNT`), passend zur KAN-457-Anforderung.

### 4.6 `uipath-erp-erfassung` — RPA-Bot / ERP
`handlers/uipath_handler.py` fängt sowohl Bot-Fehler (Queue-Item-Status `Failed`,
Timeout beim Polling) als auch technische Verbindungsfehler ab und übersetzt **alle**
in `ERR_UIPATH_FAILED`. Das Error Boundary Event leitet in die manuelle ERP-Erfassung
(Lösung aus Sprint 5). Ohne UiPath-Credentials läuft ein Simulationspfad, der über
`simulateUiPathError` gezielt einen Fehlerfall für die Demo erzeugen kann.

### 4.7 `send-information-request` / `archive-invoice` — Safety-Net-Tasks
Beide Tasks haben im BPMN keine Error Boundary:

- Fehlende/leere `invoiceId` → `BusinessError` (`ERR_INFO_REQUEST` bzw. `ERR_ARCHIVE`)
  → Incident (Safety-Net, sollte nicht auftreten).
- Dateisystem-Fehler (`OSError`) → durchgereicht → Retry → Incident.

## 5. Grenzen der aktuellen Umsetzung

Bewusst offen gelassene Punkte — relevant, um Demo-Ergebnisse richtig einzuordnen:

- **Inhaltliche Tiefe der Plausibilitätsprüfung.** Geprüft werden Vorhandensein,
  Confidence-Schwelle, Betrags- und Währungsformat. **Nicht** geprüft werden
  IBAN-Prüfsumme, Steuerlogik (amountNet/amountGross-Verhältnis exakt) oder die
  fachliche Richtigkeit der Beträge gegenüber dem PDF-Original.
- **Zahlenformat aus dem Korrekturformular.** `apply-human-review` reicht korrigierte
  Werte typtreu durch; die numerische Normalisierung (z. B. `"1.200,50"`) passiert
  erst im gRPC-/Payment-Mapping. Ein dort nicht parsebarer Betrag wird zum
  `ERR_GRPC`/`ERR_RABBITMQ`, nicht schon im Review-Schritt erkannt.
- **Keine echte Lieferanten-Schnittstelle.** Rückfragen werden als JSON protokolliert
  (`Rechnungsdaten/<invoiceId>_rueckfrage.json`); die Antwort kommt über das
  REST-Gateway/Postman als Zeebe-Message `Message_Antwort`.
- **Retry-/Timeout-Semantik** (Anzahl Wiederholungen, Backoff) wird im BPMN am
  jeweiligen Task konfiguriert, nicht im Worker-Code. Die Job-Timeouts der Handler
  liegen bei 30 s (UiPath 5 min wegen des Bot-Laufs).
- **Idempotenz.** Doppelte Zustellung desselben Jobs ist nicht eigens abgesichert;
  der gRPC-Service erkennt Duplikate über `ALREADY_EXISTS` (→ `ERR_GRPC`), der
  RabbitMQ-Schritt nicht.

## 6. Bezug zu Tests und Demo

Die Fehler-Klassifizierung ist durch Unit-Tests abgedeckt
(`worker/src/tests/`): u. a. `test_ai_extraction_mapping.py`,
`test_ai_extraction_handler.py`, `test_human_review_mapping.py`,
`test_human_review_handler.py` (BusinessError- vs. NEEDS_REVIEW- vs.
Pass-through-Fälle). Für die Demo genügt laut Scope 8.3 ein dokumentierter,
bei Bedarf demonstrierbarer Fehlerfall — am einfachsten der Human-Review-Fall
(Szenario 8.2) oder ein simulierter UiPath-Fehler (`simulateUiPathError = true`).
