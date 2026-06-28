"""Hilfsskript zum Starten des Rechnungsfreigabeprozesses über den E-Mail-Eingang.

Sendet die Nachricht 'Message_InvoiceReceived' an Zeebe, um das Message-Start-Event
auszulösen und die automatische PDF-Extraktion zu starten.
"""
import asyncio
import os
import sys
from pyzeebe import ZeebeClient, create_insecure_channel

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")


async def main():
    print(f"[Start-Script] Verbinde mit Zeebe unter {ZEEBE_ADRESSE} ...")
    
    try:
        # Verbindung aufbauen
        kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
        client = ZeebeClient(kanal)
        
        # Message_InvoiceReceived senden, um den E-Mail-Workflow-Start auszulösen.
        # Da dies ein Start-Event ist, muss der correlation_key leer sein.
        print("[Start-Script] Sende Nachricht 'Message_InvoiceReceived' mit 'beispiel_rechnung.pdf'...")
        await client.publish_message(
            name="Message_InvoiceReceived",
            correlation_key="",  # Start-Event erfordert leeren Korrelationsschlüssel
            variables={
                "fileName": "beispiel_rechnung.pdf"
            }
        )
        print("[Start-Script] \u2713 Nachricht erfolgreich gesendet! Eine neue E-Mail-Prozessinstanz wurde gestartet.")
        
    except Exception as e:
        print(f"[Start-Script] \u2717 Fehler beim Senden der Nachricht: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
