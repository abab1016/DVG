# DvG  — Digitalisierung Eingangsrechnungsbearbeitung

Technischer Prototyp zur Digitalisierung der Eingangsrechnungsbearbeitung mit gRPC-Service, Zahlungssystem über Messaging und Client.

## Architektur

```
Client ──gRPC──▶ gRPC-Service (Rechnungsmetadaten) ──▶ Speicher
  │
  └──Async──▶ Message Broker ──Messaging──▶ Zahlungssystem
```

## Komponenten

| Komponente     | Beschreibung                          |
|----------------|---------------------------------------|
| `grpc-service` | Speichert/liefert Rechnungsmetadaten  |
| `zahlungssystem` | Empfängt und verarbeitet Zahlungen  |
| `client`       | Erfasst Rechnungen, löst Zahlung aus  |
| Message Broker | Puffert und leitet Zahlungsaufträge   |

## Schnellstart

```bash
# 1. Repo Befehle
git clone  https://github.com/abab1016/DVG.git && cd DvG

git init 
git add .
git commit -m "Initial commit"  
git remote add origin https://github.com/abab1016/DVG.git
git push origin main

```

## Team

- [Sam Haghighi]
- [Efe Yueksei]
- [Nick Rusnak]
- [Abubakar Abdi Tube]
