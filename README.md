# DvG  — Digitalisierung Eingangsrechnungsbearbeitung

Technischer Prototyp zur Digitalisierung der Eingangsrechnungsbearbeitung mit gRPC-Service, Zahlungssystem über Messaging und Client.

## Architektur

### Rechnungs_metadatenmodell.json

```json
{
  "invoiceId": "INV-2026-001",
  "supplierId": "SUP-123",
  "supplierName": "Muster GmbH",
  "invoiceDate": "2026-04-06",
  "dueDate": "2026-05-06",
  "amountNet": 1000.00,
  "amountGross": 1190.50,
  "currency": "EUR",
  "iban": "DE89370400440532013000",
  "status": "OPEN",
  "fileName": "invoice_2026_001.pdf",
  "createdAt": "2026-04-06T10:30:00Z"
}
```

![1775497530429](images/README/1775497530429.png)







## Komponenten


| Komponente       | Beschreibung                          |
| ---------------- | ------------------------------------- |
| `grpc-service`   | Speichert/liefert Rechnungsmetadaten  |
| `zahlungssystem` | Empfängt und verarbeitet Zahlungen   |
| `client`         | Erfasst Rechnungen, löst Zahlung aus |
| Message Broker   | Puffert und leitet Zahlungsaufträge  |

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

- Sam Haghighi
- Efe Yueksei
- Nick Rusna
- Abubakar Abdi Tube
