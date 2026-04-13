# DVG — Digitalisierung Eingangsrechnungsbearbeitung

Prototyp zur Digitalisierung der Eingangsrechnungsbearbeitung. Rechnungsmetadaten werden per gRPC gespeichert, der Zahlungsauftrag geht asynchron über RabbitMQ ans Zahlungssystem.

## Architektur

![Architekturdiagramm](images/README/1775498351364.png)

Der Ablauf teilt sich in zwei Schritte auf:

Zuerst schickt der Client die Rechnungsmetadaten per gRPC an den Service. Der Service prüft die Eingabe, legt eine JSON-Datei an und gibt die bestätigte Invoice-ID zurück. Erst wenn das geklappt hat, geht es weiter.

Im zweiten Schritt baut der Client mit der bestätigten ID einen Zahlungsauftrag und schreibt ihn in die RabbitMQ-Warteschlange `zahlungsauftraege`. Das Zahlungssystem liest die Nachricht, gibt sie aus und protokolliert den Status in `Rechnungsdaten/zahlungslog.json`.

## Voraussetzungen

- Python 3.9 oder neuer
- Docker Desktop (für RabbitMQ)

Abhängigkeiten installieren:

```bash
pip install grpcio grpcio-tools pika pytest
```

Proto-Stubs generieren — das muss einmalig gemacht werden, und wieder wenn sich `invoice.proto` ändert:

```bash
cd grpc-service/src
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/invoice.proto
```

## Schnellstart

Am einfachsten geht es mit dem Demo-Skript, das alles in der richtigen Reihenfolge startet:

```bash
# Interaktives Menü:
bash demo.sh

# Demo-Rechnung direkt durchlaufen, ohne Menü:
bash demo.sh --demo
```

Das Skript startet RabbitMQ, wartet bis es bereit ist, dann gRPC-Service und Zahlungssystem im Hintergrund, und öffnet schließlich den Client. Strg+C beendet alles sauber.

## Manuell starten

Wer die einzelnen Komponenten lieber selbst starten will, braucht vier Terminals. Die Reihenfolge ist wichtig: RabbitMQ muss vor dem Consumer laufen, der gRPC-Service vor dem Client.

**Terminal 1 — RabbitMQ**

```bash
docker compose up -d rabbitmq
```

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

**Terminal 4 — Client**

```bash
cd client/src

# Interaktives Menü:
python ui.py

# Demo-Rechnung direkt:
python client.py

# Eigene Rechnung aus Datei:
python client.py --file meine-rechnung.json
```

## Client verwenden

Der Client ist der Einstiegspunkt für Benutzer. Er erfasst Rechnungsdaten, speichert sie per gRPC und löst die Zahlung aus.

**Interaktives Menü (`ui.py`):**

```
  [1]  Demo-Rechnung verarbeiten
  [2]  Rechnung manuell eingeben
  [3]  Rechnung aus JSON-Datei laden
  [0]  Beenden
```

Option 1 lädt die eingebaute Demo-Rechnung (Muster GmbH, 1190,50 EUR) und fragt kurz nach Bestätigung. Option 2 fragt alle Felder ab, bei jedem steht der Standardwert in Klammern — Enter übernimmt ihn einfach. Option 3 erwartet den Pfad zu einer JSON-Datei.

**Rechnung direkt aus Datei verarbeiten (`client.py`):**

```bash
cd client/src
python client.py --file /pfad/zur/rechnung.json
```

Wenn der gRPC-Service nicht erreichbar ist, bricht der Client mit einer klaren Fehlermeldung ab. Die Zahlung wird nur ausgelöst, wenn das Speichern zuvor erfolgreich war.

## Eigene Rechnung als JSON

Alle Felder müssen vorhanden sein:

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
  "status":       "OPEN",
  "fileName":     "rechnung_april.pdf",
  "createdAt":    "2026-04-10T09:00:00Z"
}

Der Betrag im Zahlungsauftrag ist immer `amountGross`.

## Gespeicherte Dateien

Der Ordner `Rechnungsdaten/` wird automatisch angelegt. Darin liegt nach einem Durchlauf:

- `INV-2026-001.json` — die Rechnungsmetadaten, die der gRPC-Service gespeichert hat
- `zahlungslog.json` — das Protokoll des Zahlungssystems, wird bei jeder Zahlung erweitert

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


| Variable         | Standard                        | Beschreibung             |
| ---------------- | ------------------------------- | ------------------------ |
| `GRPC_ADRESSE`   | `localhost:50051`               | Adresse des gRPC-Service |
| `GRPC_ZEITLIMIT` | `5`                             | Zeitlimit in Sekunden    |
| `BROKER_ADRESSE` | `amqp://guest:guest@localhost/` | RabbitMQ-Verbindung      |

## RabbitMQ-Verwaltungsoberfläche

Unter `http://localhost:15672` gibt es eine grafische Oberfläche (Benutzer: `guest`, Passwort: `guest`). Dort ist die Warteschlange `zahlungsauftraege` mit der Anzahl wartender Nachrichten sichtbar.

## Tests

```bash
python -m pytest grpc-service/tests/ client/src/tests/ zahlungssystem/src/tests/ -v
```

27 Tests, kein laufender Service nötig — gRPC und RabbitMQ werden simuliert.


| Testdatei                                   | Tests | Inhalt                                                                                                                                  |
| ------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `grpc-service/tests/test_server.py`         | 7     | Speichern, Datei anlegen, leere ID, Leerzeichen-ID, doppelte ID, Abrufen, nicht gefunden                                                |
| `client/src/tests/test_grpc_client.py`      | 6     | Erfolg, Kanal schließen, Server weg, Timeout, ungültige Eingabe,`success=False`                                                       |
| `client/src/tests/test_payment_producer.py` | 7     | Auftragsfelder, bestätigte ID, Bruttobetrag, Warteschlange, Persistenz, Verbindung schließen, Verbindungsfehler                       |
| `zahlungssystem/src/tests/test_consumer.py` | 7     | Bestätigung, Ausgabe, NACK bei JSON-Fehler, NACK bei fehlendem Feld, NACK bei negativem Betrag, Eintrag schreiben, Einträge anhängen |

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

Der gRPC-Client unterscheidet folgende Fehlerfälle und gibt jeweils eine lesbare Meldung aus: `UNAVAILABLE` (Service nicht gestartet), `DEADLINE_EXCEEDED` (Antwort dauert zu lang), `INVALID_ARGUMENT` (fehlerhafte Daten), `INTERNAL` (Fehler auf Server-Seite).

## Projektstruktur

```
DVG/
  grpc-service/
    src/
      proto/
        invoice.proto          # Schnittstellendefinition
      invoice_pb2.py           # generiert
      invoice_pb2_grpc.py      # generiert
      server.py                # gRPC-Server
    tests/
      conftest.py
      test_server.py
    requirements.txt
  zahlungssystem/
    src/
      consumer.py              # RabbitMQ-Consumer
      tests/
        conftest.py
        test_consumer.py
    requirements.txt
  client/
    src/
      grpc_client.py           # gRPC-Aufruf mit Fehlerbehandlung
      payment_producer.py      # Zahlungsauftrag bauen und senden
      client.py                # nicht-interaktiver Einstiegspunkt
      ui.py                    # interaktives Menü
      tests/
        conftest.py
        test_grpc_client.py
        test_payment_producer.py
    requirements.txt
  Rechnungsdaten/              # JSON-Dateien pro Rechnung + zahlungslog.json
  docker-compose.yml
  demo.sh
```

## Team

- Sam Haghighi (hasa1034)
- Efe Yueksei (yuce1011)
- Nick Rusna (runi1015)
- Abubakar Abdi Tube (abab1016)
