import asyncio
import os
import sys
from pathlib import Path

from pyzeebe import ZeebeClient, create_insecure_channel

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")

# Plattform aus plattform.txt auslesen oder auto-detektieren
PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
plattform_file = PROJEKT_WURZEL / "plattform.txt"
plattform = "mac"

if plattform_file.exists():
    with plattform_file.open("r", encoding="utf-8") as f:
        plattform = f.read().strip().lower()
else:
    if sys.platform.startswith("win"):
        plattform = "windows"

# BPMN-Ressourcen liegen auf allen Plattformen im Projektordner.
sprint_path = PROJEKT_WURZEL / "BPMN"
bpmn_file_standard = sprint_path / "G7_Rechnungsfreigabe.bpmn"
bpmn_file_uipath = sprint_path / "G7_Rechnungsfreigabe_with_UiPath.bpmn"
bpmn_file_ai = sprint_path / "G7_Rechnungsfreigabe_with_AI.bpmn"
forms_dir = sprint_path / "Forms"

print(f"[Deploy] Verwende Plattform: '{plattform}'")
print(f"[Deploy] Lade Standard BPMN aus: {bpmn_file_standard}")
print(f"[Deploy] Lade UiPath BPMN aus: {bpmn_file_uipath}")
print(f"[Deploy] Lade AI BPMN aus: {bpmn_file_ai}")
print(f"[Deploy] Lade Forms aus: {forms_dir}")

RESSOURCEN = [
    # bpmn_file_standard,  # Altes BPMN ohne AI – nicht mehr deployen
    # bpmn_file_uipath,    # UiPath BPMN – nicht mehr deployen
    bpmn_file_ai,
    forms_dir / "compliance-regeln.dmn",
    forms_dir / "Compliance_Check.form",
    forms_dir / "ERP_Bestaetigung.form",
    forms_dir / "Manuelle_Archivierung.form",
    forms_dir / "Manuelle_Speicherung.form",
    forms_dir / "Manuelle_Zahlung.form",
    forms_dir / "Metadaten_Erfassung.form",
    forms_dir / "Portal_Start.form",
    forms_dir / "Rechnungs_Pruefung.form",
    forms_dir / "Rueckfrage.form",
    forms_dir / "Manager_Pruefung.form",
]


async def main() -> None:
    # Überprüfen, ob alle Dateien existieren
    for res in RESSOURCEN:
        if not res.exists():
            print(f"[Deploy] Fehler: Datei existiert nicht: {res}")
            sys.exit(1)

    kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
    client = ZeebeClient(kanal)
    antwort = await client.deploy_resource(*(str(res) for res in RESSOURCEN))
    for d in antwort.deployments:
        print(d)


if __name__ == "__main__":
    asyncio.run(main())
