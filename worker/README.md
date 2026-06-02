# Worker (Sprint 4)

pyzeebe-basierter Worker, der Camunda 8 mit den Sprint-1-Komponenten verbindet.
Deckt die Subtasks **4.1–4.7** aus KAN-235 ab (alle Handler fertig, E2E-Test steht noch aus).

## Verzeichnisstruktur

```
worker/
  src/
    worker.py                 # Entry-Point, Zeebe-Channel + alle Handler
    handlers/
      grpc_handler.py         # Job-Handler "save-invoice-metadata"
      payment_handler.py      # Job-Handler "send-payment-order"
      archive_handler.py      # Job-Handler "archive-invoice"
    mapping/
      grpc_mapping.py         # Zeebe-Variablen → Rechnungsmetadaten (proto)
      payment_mapping.py      # Zeebe-Variablen → Zahlungsauftrag (RabbitMQ)
    tests/
      test_grpc_mapping.py    # Unit-Tests Mapping (9)
      test_grpc_handler.py    # Unit-Tests gRPC-Handler (8)
      test_payment_mapping.py # Unit-Tests Payment-Mapping (9)
      test_payment_handler.py # Unit-Tests Payment-Handler (5)
      test_archive_handler.py # Unit-Tests Archivierungs-Handler (5)
  requirements.txt
```

```## Camunda 8 starten

```powershell
docker compose up -d elasticsearch zeebe operate tasklist
```
Bereit, wenn:

- Zeebe: `http://localhost:9600/actuator/health` liefert `UP`
- Operate:  http://localhost:8081  (Login `demo` / `demo`)
- Tasklist: http://localhost:8082  (Login `demo` / `demo`)

## gRPC-Service starten

```powershell
cd grpc-service/src
python server.py
```
## Worker starten

```powershell
cd worker/src
python worker.py
```
Erwartete Log-Zeilen:

```
... INFO [worker] Starte Worker, verbinde mit Zeebe: localhost:26500
... INFO [worker] Worker bereit, abonniere Job-Types: save-invoice-metadata, send-payment-order, archive-invoice
```
## Tests

```powershell
cd worker/src
python -m pytest tests/ -v
```
## Umgebungsvariablen


| Variable         | Standard          | Beschreibung                  |
| ---------------- | ----------------- | ----------------------------- |
| `ZEEBE_ADRESSE`  | `localhost:26500` | Adresse des Zeebe-Gateways    |
| `GRPC_ADRESSE`   | `localhost:50051` | gRPC-Service (aus Sprint 1)   |
| `GRPC_ZEITLIMIT` | `5`               | Timeout in Sekunden für gRPC |

## Job-Types


| Job-Type                | Subtask | Status        |
| ----------------------- | ------- | ------------- |
| `save-invoice-metadata` | KAN-266 | implementiert |
| `send-payment-order`    | KAN-268 | implementiert |
| `archive-invoice`       | KAN-269 | implementiert |

> Job-Type-Namen müssen mit dem BPMN-Modell in KAN-233 abgestimmt sein.

## Fehlerverhalten

Alle Handler folgen derselben Logik: **Datenfehler → BusinessError →
BPMN Error Boundary; Infrastrukturfehler → Retry → Incident.**

### `save-invoice-metadata`


| Auslöser                                         | Reaktion              | BPMN-Verhalten                    |
| ------------------------------------------------- | --------------------- | --------------------------------- |
| Mapping-Fehler (fehlendes/ungültiges Feld)       | `BusinessError`       | Error Boundary`ERR_GRPC`          |
| gRPC`INVALID_ARGUMENT`                            | `BusinessError`       | Error Boundary`ERR_GRPC`          |
| gRPC`ALREADY_EXISTS`                              | `BusinessError`       | Error Boundary`ERR_GRPC`          |
| gRPC`NOT_FOUND`                                   | `BusinessError`       | Error Boundary`ERR_GRPC`          |
| Service-Antwort mit`success=False` (RuntimeError) | `BusinessError`       | Error Boundary`ERR_GRPC`          |
| gRPC`UNAVAILABLE` / `DEADLINE_EXCEEDED`           | Exception (re-raised) | Zeebe-Retry, danach Incident      |
| gRPC`INTERNAL`                                    | Exception (re-raised) | Zeebe-Retry, danach Incident      |

### `send-payment-order`


| Auslöser                                   | Reaktion              | BPMN-Verhalten               |
| ------------------------------------------- | --------------------- | ---------------------------- |
| Mapping-Fehler (fehlendes/ungültiges Feld) | `BusinessError`       | Error Boundary`ERR_RABBITMQ` |
| `AMQPConnectionError`                       | Exception (re-raised) | Zeebe-Retry, danach Incident |
| Sonstiger`AMQPError`                        | Exception (re-raised) | Zeebe-Retry, danach Incident |

### `archive-invoice`


| Auslöser                                 | Reaktion              | BPMN-Verhalten                          |
| ----------------------------------------- | --------------------- | --------------------------------------- |
| invoiceId null/leer                       | `BusinessError`       | keine Boundary im BPMN → Incident       |
| `OSError` (Datei schreiben schlägt fehl) | Exception (re-raised) | Zeebe-Retry, danach Incident            |

## Wiederverwendung aus Sprint 1

Der Worker importiert direkt aus `client/src/`:

- `grpc_client.speichere_rechnung()` — gRPC-Aufruf mit Fehlerbehandlung
- `payment_producer.sende_zahlungsauftrag()` (wird in KAN-268 genutzt)

Damit bleibt die Logik aus Sprint 1 unverändert; der Worker ist nur der
Adapter zwischen Zeebe-Job-Protokoll und den existierenden Funktionen.
