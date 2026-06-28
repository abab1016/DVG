# Datenvertrag: Korrigierte Human-Review-Daten → Camunda-Prozess (Sprint 6, KAN-457)

Ergänzt [`datenvertrag_ai_extraction.md`](datenvertrag_ai_extraction.md) um den
Rückweg: Nachdem die Plausibilitätsprüfung `NEEDS_REVIEW` ergeben hat und ein
Sachbearbeiter im User-Task korrigiert hat, führt der Service-Task
`apply-human-review` die Korrekturen mit den AI-Daten zusammen. Code:
`worker/src/mapping/human_review_mapping.py`, `worker/src/handlers/human_review_handler.py`.

## 1. Eingabeformat (`humanReviewData`)

Das Review-Formular schreibt die korrigierten Felder als **eine** Prozessvariable
`humanReviewData` — ein Objekt `{feldname: wert}` (oder ein JSON-String desselben).
Symmetrisch zu `aiExtractionData` auf dem Hinweg.

Korrigierbar sind ausschließlich die fachlichen Felder aus dem AI-Datenvertrag:

| Feld | Bedeutung |
| --- | --- |
| `invoiceNumber` | fachliche Rechnungsnummer |
| `supplierName`, `invoiceDate`, `currency`, `iban`, `billingAddress` | Kopfdaten |
| `amountGross`, `amountNet`, `dueDate` | Beträge / Fälligkeit |

`invoiceId` ist **bewusst nicht korrigierbar** (read-only): Es ist der technische
Korrelationsschlüssel der Zeebe-Messages und darf mitten im laufenden Prozess nicht
überschrieben werden — er wird stets unverändert aus den Prozessvariablen übernommen.
Ein vom Formular gesendeter `invoiceId`-Wert wird ignoriert. Korrigieren lässt sich
nur die fachliche `invoiceNumber`.

Felder, die nicht in dieser Liste stehen (`invoiceId`, `channel`,
`aiPlausibilityStatus`, `confidence`, beliebige Formular-Extrafelder), werden
**ignoriert** und gelangen nicht in die Prozessvariablen.

## 2. Merge-Regeln

1. **Korrektur hat Vorrang** vor dem AI-Wert. Ein leer gelassenes Feld (`""`/None)
   gilt als "nicht korrigiert" → der AI-Wert bleibt erhalten.
2. **invoiceId/invoiceNumber** müssen nach dem Merge konsistent (nicht leer)
   vorliegen, sonst → `BusinessError(ERR_HUMAN_REVIEW)` zurück in die manuelle
   Bearbeitung. `invoiceId` stammt dabei immer aus den Prozessvariablen (read-only),
   nur `invoiceNumber` kann der Mensch korrigieren.
3. Kein Eintrag wird gelöscht — der Schritt liefert nur die übernommenen Korrekturen
   plus die konsistente ID zurück (pyzeebe merged sie in die Prozessvariablen).

## 3. Ausgabe (Prozessvariablen)

| Variable | Inhalt |
| --- | --- |
| korrigierte Felder | die tatsächlich übernommenen Werte |
| `invoiceId`, `invoiceNumber` | normalisiert als nicht-leere Strings |
| `humanReviewApplied` | `true`, wenn eine Prüfung stattfand |
| `humanReviewKorrekturen` | Liste der geänderten Feldnamen (Nachvollziehbarkeit) |
| `aiPlausibilityStatus` | `REVIEWED` nach erfolgter Prüfung; `aiReviewGruende` → `[]` |

Die nachgelagerten Schritte `save-invoice-metadata` (gRPC) und `send-payment-order`
(RabbitMQ) bleiben **unverändert** und lesen die jetzt korrigierten Variablen.