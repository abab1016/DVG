"""Automatisierungsskript für den E-Mail-Start des Rechnungsfreigabeprozesses.

Dieses Skript vereint zwei Schritte in einem Befehl:
1. Inkrementelle Generierung einer neuen Rechnungs-PDF (beispiel_rechnung.pdf).
2. Sofortiges Senden der Startnachricht an Zeebe, um den Prozess zu starten.
"""
import asyncio
import os
import sys
from pathlib import Path
from pyzeebe import ZeebeClient, create_insecure_channel

# Importiere Generierungslogik aus create_beispiel_rechnung.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_beispiel_rechnung import hole_naechsten_zaehler, erstelle_pdf

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")


async def main():
    print("=== Automatischer E-Mail-Prozessstart ===")

    # Schritt 1: PDF erstellen
    print("\n[Schritt 1] Generiere neue PDF-Rechnung...")
    cnt = hole_naechsten_zaehler()
    datei_name = erstelle_pdf(cnt)

    # Schritt 2: Zeebe Trigger
    print("\n[Schritt 2] Sende Startnachricht an Zeebe...")
    try:
        kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
        client = ZeebeClient(kanal)

        await client.publish_message(
            name="Message_InvoiceReceived",
            correlation_key="",  # Leer fuer Start-Events
            variables={
                "fileName": datei_name
            }
        )
        print(f"\n[OK] ERFOLG: Prozess gestartet fuer Rechnung INV-2026-{cnt}!")
        print("Die Aufgabe ist nun in der Camunda Tasklist sichtbar.")

    except Exception as e:
        print(f"\n[FEHLER] Prozess konnte nicht gestartet werden: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
