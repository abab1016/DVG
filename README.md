# DVG: Digitalisierung Eingangsrechnungsbearbeitung

Prototyp zur Digitalisierung der Eingangsrechnungsbearbeitung. Ein Camunda-8-Workflow steuert den Ablauf: Rechnungsmetadaten werden per gRPC gespeichert, der Zahlungsauftrag geht asynchron über RabbitMQ ans Zahlungssystem.


Wichtig: In der plattform.txt muss entweder "mac" oder "windows" hinterlegt sein! Entscheidend ist das lokale OS.

## Architektur

![Architekturdiagramm](images/README/1775498351364.png)

Seit Sprint 4 orchestriert **Camunda 8** den Prozess. Ein Python-Worker (`pyzeebe`) abonniert die Service-Tasks des BPMN-Modells und ruft die in Sprint 1 gebauten Bausteine auf:

Im Service-Task `save-invoice-metadata` schickt der Worker die Rechnungsmetadaten per gRPC an den Service. Der Service prüft die Eingabe, legt eine JSON-Datei an und gibt die bestätigte Invoice-ID zurück.

Im Service-Task `send-payment-order` baut der Worker mit der bestätigten ID einen Zahlungsauftrag und schreibt ihn in die RabbitMQ-Warteschlange `zahlungsauftraege`. Das Zahlungssystem liest die Nachricht und protokolliert den Status in `Rechnungsdaten/zahlungslog.json`.

Im Service-Task `archive-invoice` schreibt der Worker zum Abschluss eine Datei `Rechnungsdaten/<invoiceId>_abschluss.json`.

Fachliche Fehler (ungültige Daten, Duplikate) wirft der Worker als BPMN-`BusinessError` an ein Error-Boundary-Event; technische Fehler (gRPC/RabbitMQ nicht erreichbar) führen zu Zeebe-Retry und ggf. einem Incident.

## Voraussetzungen

- Python 3.9 oder neuer
- Docker Desktop (für RabbitMQ und Camunda 8)

Abhängigkeiten installieren:

```bash
pip install grpcio grpcio-tools pika pyzeebe pytest pytest-asyncio
```

Proto-Stubs generieren — das muss einmalig gemacht werden, und wieder wenn sich `invoice.proto` ändert:

```bash
cd grpc-service/src
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/invoice.proto
```

## Schnellstart

Am einfachsten geht es mit dem Demo-Skript, das alles in der richtigen Reihenfolge startet:

```bash
bash demo.sh
```

Das Skript startet RabbitMQ und Camunda 8 (Zeebe/Operate/Tasklist), wartet bis Zeebe bereit ist, startet dann gRPC-Service und Zahlungssystem im Hintergrund und schließlich den pyzeebe-Worker im Vordergrund. Strg+C beendet die Hintergrundprozesse sauber.

Der Worker wartet anschließend auf Jobs. Um den Prozess auszulösen:

1. BPMN `images/Eingangsrechnungsbearbeitung.bpmn` im Camunda Modeler auf Zeebe (`localhost:26500`) deployen.
2. Prozessinstanz mit den Rechnungs-Variablen starten (siehe [Prozessvariablen](#prozessvariablen)).
3. Ablauf in Operate (`http://localhost:8081`, Login `demo`/`demo`) verfolgen.

## Manuell starten

Wer die Komponenten lieber selbst startet, braucht mehrere Terminals. Reihenfolge: RabbitMQ vor dem Consumer, Camunda und gRPC-Service vor dem Worker.

**Terminal 1 — RabbitMQ + Camunda 8**

```bash
docker compose up -d rabbitmq elasticsearch zeebe operate tasklist
```

Bereit, wenn `http://localhost:9600/actuator/health` `UP` liefert. Operate: `http://localhost:8081`, Tasklist: `http://localhost:8082` (jeweils `demo`/`demo`).

**Terminal 2 — gRPC-Service**

```bash
cd grpc-service/src
python server.py
```

Bereit, wenn `[gRPC-Server] Läuft auf Port 50051` erscheint.

**Terminal 3 — Zahlungssystem**

```bash
cd zahlungssystem/src
python consumer.py
```

Bereit, wenn `Warte auf Nachrichten in 'zahlungsauftraege' ...` erscheint.

**Terminal 4 — Worker**

```bash
cd worker/src
python worker.py
```

Bereit, wenn `Worker bereit, abonniere Job-Types: save-invoice-metadata, send-payment-order, archive-invoice` erscheint. Details zum Worker in [`worker/README.md`](worker/README.md).

## Prozessvariablen

Die Prozessinstanz wird mit diesen Variablen gestartet. Pflichtfelder für `save-invoice-metadata` und `send-payment-order`:

```json
{
  "invoiceId":    "INV-2026-099",
  "supplierId":   "SUP-456",
  "supplierName": "Beispiel AG",
  "invoiceDate":  "2026-04-10",
  "dueDate":      "2026-05-10",
  "amountNet":    500.00,
  "amountGross":  595.00,
  "currency":     "EUR",
  "iban":         "DE12345678901234567890",
  "channel":      "EMAIL",
  "invoiceNumber":"RE-2026-099",
  "fileName":     "rechnung_april.pdf"
}
```

Der Betrag im Zahlungsauftrag ist immer `amountGross`. Die genaue Feldzuordnung (welche Variable in welchen Service-Task geht) steht in [`worker/BPMN_VERTRAG.md`](worker/BPMN_VERTRAG.md).

## Gespeicherte Dateien

Der Ordner `Rechnungsdaten/` wird automatisch angelegt. Darin liegt nach einem Durchlauf:

- `<invoiceId>.json` — die Rechnungsmetadaten, die der gRPC-Service gespeichert hat
- `zahlungslog.json` — das Protokoll des Zahlungssystems, wird bei jeder Zahlung erweitert
- `<invoiceId>_abschluss.json` — die Abschlussdatei, die der Worker beim Archivieren schreibt

Das Statusprotokoll sieht so aus:

```json
[
  {
    "invoiceId": "INV-2026-001",
    "status":    "BEZAHLT",
    "zeitpunkt": "2026-04-10T08:01:00Z",
    "betrag":    1190.50,
    "waehrung":  "EUR"
  }
]
```

## Umgebungsvariablen

Ohne Konfiguration funktioniert alles mit den Standardwerten. Für andere Setups:


| Variable         | Standard                        | Beschreibung                        |
| ---------------- | ------------------------------- | ----------------------------------- |
| `ZEEBE_ADRESSE`  | `localhost:26500`               | Adresse des Zeebe-Gateways (Worker) |
| `GRPC_ADRESSE`   | `localhost:50051`               | Adresse des gRPC-Service            |
| `GRPC_ZEITLIMIT` | `5`                             | gRPC-Zeitlimit in Sekunden          |
| `BROKER_ADRESSE` | `amqp://admin:admin@localhost/` | RabbitMQ-Verbindung                 |

## RabbitMQ-Verwaltungsoberfläche

Unter `http://localhost:15672` gibt es eine grafische Oberfläche (Benutzer: `admin`, Passwort: `admin`). Dort ist die Warteschlange `zahlungsauftraege` mit der Anzahl wartender Nachrichten sichtbar.

## Tests

```bash
python -m pytest grpc-service/tests/ client/src/tests/ zahlungssystem/src/tests/ worker/src/tests/ -v
```

68 Tests, kein laufender Service nötig gRPC, RabbitMQ und Zeebe werden simuliert.


| Testdatei                                   | Tests | Inhalt                                                                                                                                  |
| ------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `grpc-service/tests/test_server.py`         | 7     | Speichern, Datei anlegen, leere ID, Leerzeichen-ID, doppelte ID, Abrufen, nicht gefunden                                                |
| `client/src/tests/test_grpc_client.py`      | 6     | Erfolg, Kanal schließen, Server weg, Timeout, ungültige Eingabe,`success=False`                                                       |
| `client/src/tests/test_payment_producer.py` | 7     | Auftragsfelder, bestätigte ID, Bruttobetrag, Warteschlange, Persistenz, Verbindung schließen, Verbindungsfehler                       |
| `zahlungssystem/src/tests/test_consumer.py` | 7     | Bestätigung, Ausgabe, NACK bei JSON-Fehler, NACK bei fehlendem Feld, NACK bei negativem Betrag, Eintrag schreiben, Einträge anhängen |
| `worker/src/tests/test_grpc_mapping.py`     | 12    | Variablen→Proto-Mapping, Pflichtfelder, Betragsprüfung, nur Proto-Felder                                                              |
| `worker/src/tests/test_grpc_handler.py`     | 8     | Erfolg, Fehlerklassifizierung (BusinessError vs. Retry), Null-Guard                                                                     |
| `worker/src/tests/test_payment_mapping.py`  | 10    | Variablen→Zahlungsauftrag, Pflichtfelder, positiver Betrag, optionale Felder                                                           |
| `worker/src/tests/test_payment_handler.py`  | 5     | Erfolg, AMQP-Fehler→Retry, Job-Variablen                                                                                               |
| `worker/src/tests/test_archive_handler.py`  | 6     | Abschlussdatei schreiben, Null-Guard, OSError→Retry                                                                                    |



`client/src/client.py` und `ui.py` sind die Standalone-Demo aus Sprint 1. Sie laufen nur, wenn man sie manuell startet, und werden vom Worker nicht benutzt  der Worker übernimmt die Orchestrierung. Zum reinen Testen von gRPC + RabbitMQ ohne Camunda funktionieren sie weiterhin.

## gRPC-Schnittstelle

Definition liegt in `grpc-service/src/proto/invoice.proto`:

```protobuf
service RechnungsService {
  rpc SpeichereRechnungsmetadaten (Rechnungsmetadaten) returns (SpeicherAntwort);
  rpc HoleRechnungsmetadaten      (RechnungsAnfrage)   returns (Rechnungsmetadaten);
}
```

`SpeichereRechnungsmetadaten` speichert eine Rechnung und gibt die bestätigte Rechnungs-ID zurück. Leere Rechnungs-ID bekommt `INVALID_ARGUMENT` zurück.

`HoleRechnungsmetadaten` liest eine gespeicherte Rechnung anhand der ID. Existiert sie nicht, kommt `NOT_FOUND`.
