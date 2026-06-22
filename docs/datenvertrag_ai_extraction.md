# Datenvertrag: AI-Extraction-JSON → Camunda-Prozess (Sprint 6, Vorgang 4)

Status: Phase 1 (Entwurf, gestartet 16.06.2026). Definiert das JSON-Format, das n8n/LLM
(Vorgang 2) liefern muss, und die Validierungs-/Mapping-Logik, die daraus Camunda-
Prozessvariablen macht. Code: `worker/src/mapping/ai_extraction_mapping.py`.

## 1. Eingabeformat (AI-Extraction-JSON)

n8n/das LLM liefert pro verarbeiteter PDF-Rechnung ein JSON-Objekt:

| Feld | Pflicht | Typ | Bedeutung |
| --- | --- | --- | --- |
| `invoiceId` | ja | string | Eindeutige Rechnungs-ID |
| `invoiceNumber` | ja | string | Rechnungsnummer |
| `supplierName` | ja | string | Lieferantenname |
| `invoiceDate` | ja | string (`YYYY-MM-DD`) | Rechnungsdatum |
| `amountGross` | ja | number | Bruttobetrag |
| `currency` | ja | string (3 Buchstaben) | Währung, z. B. `EUR` |
| `iban` | ja | string | IBAN des Lieferanten |
| `billingAddress` | ja | string | Rechnungsadresse |
| `dueDate` | optional | string (`YYYY-MM-DD`) | Fälligkeitsdatum |
| `amountNet` | optional | number | Nettobetrag |
| `invoiceItems` | optional | array von `{description, quantity, unitPrice, totalPrice}` | Rechnungspositionen |
| `confidence` | empfohlen | object `{feldname: 0.0–1.0}` | Confidence-Wert pro Pflichtfeld |
| `sourceFile` | optional | string | Name der verarbeiteten PDF |
| `extractionEngine` | optional | string | z. B. `n8n+gemini-1.5`, nur zur Doku |

Die Pflichtfelder entsprechen bewusst denen, die bisher `pdf_handler.py` per Regex
extrahiert hat (`worker/src/handlers/pdf_handler.py`, Zeile 64) — das AI-JSON ersetzt
diese Quelle, ohne die Abnehmer (gRPC-Mapping) umzubenennen.

Beispiele: [`worker/src/mapping/beispiele/ai_extraktion_happy_path.json`](../worker/src/mapping/beispiele/ai_extraktion_happy_path.json),
[`worker/src/mapping/beispiele/ai_extraktion_human_review.json`](../worker/src/mapping/beispiele/ai_extraktion_human_review.json).

## 2. Plausibilitätsregeln und Confidence-Logik

`pruefe_plausibilitaet()` prüft:

1. Alle Pflichtfelder vorhanden und nicht leer.
2. Für jedes Pflichtfeld liegt eine Confidence vor und ist ≥ `CONFIDENCE_SCHWELLE` (aktuell `0.85`).
3. `amountGross`/`amountNet` sind numerisch, nicht negativ, `amountGross >= amountNet`.
4. `currency` ist ein gültiges 3-Buchstaben-Format.

Ergebnis ist `"VALID"` oder `"NEEDS_REVIEW"` plus eine Liste lesbarer Gründe (für das
Human-Review-Formular aus Vorgang 3). Anders als bei `grpc_mapping.py` führt eine
unsichere oder unvollständige Eingabe **nicht** zu einem Fehler/Incident, sondern zu
einer Routing-Entscheidung — das entspricht dem Soll-Prozess aus dem Scope-Dokument
(Abschnitt 5.2: `Gateway "Plausibilität ausreichend?"`).

`MappingFehler` wird nur bei strukturell kaputtem Input geworfen (z. B. kein JSON-Objekt).

## 3. Mapping auf Camunda-Prozessvariablen

`ai_daten_zu_prozessvariablen()` übernimmt die Feldnamen unverändert in die
Prozessvariablen, ergänzt `channel: "EMAIL"` (wie bisher `pdf_handler.py`) und
`fileName` aus `sourceFile`. Zusätzlich werden `aiPlausibilityStatus` und
`aiReviewGruende` gesetzt, die das neue BPMN-Gateway für die Human-Review-Verzweigung
auswertet.

Das Ergebnis ist absichtlich kompatibel mit `grpc_mapping.EINGABE_PFLICHT`
(`worker/src/mapping/grpc_mapping.py`, Zeile 25) — der bestehende
`save-invoice-metadata`-Schritt benötigt keine Anpassung, solange er nur die bekannten
Felder liest.

## 4. Offen für Phase 2

- Welcher Job-Type/Service-Task im BPMN diese Funktionen aufruft (`validate-ai-extraction`
  o. ä.) — abhängig von Nicks n8n/Camunda-Integration (Vorgang 2).
- Anbindung im Worker (`worker/src/worker.py`) und Registrierung eines neuen Handlers.
- Feinschliff der Plausibilitätsregeln anhand echter LLM-Ausgaben (z. B. IBAN-Prüfsumme).
- Tests bereits gestartet: `worker/src/tests/test_ai_extraction_mapping.py`.
