import asyncio
import os
import sys

from pyzeebe import ZeebeClient, create_insecure_channel

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")

# Plattform aus plattform.txt auslesen oder auto-detektieren
hier = os.path.dirname(os.path.abspath(__file__))
plattform_file = os.path.join(hier, "plattform.txt")
plattform = "mac"

if os.path.exists(plattform_file):
    with open(plattform_file, "r", encoding="utf-8") as f:
        plattform = f.read().strip().lower()
else:
    if sys.platform.startswith("win"):
        plattform = "windows"

# Bestimmen des Pfads für BPMN-Dateien und Forms
if plattform == "windows":
    sprint_path = r"C:\Users\abuba\Downloads\Sprint 4"
    if not os.path.exists(sprint_path):
        print(f"[Deploy] Windows-Pfad {sprint_path} existiert nicht. Verwende relativen Pfad.")
        sprint_path = os.path.join(hier, "BPMN")
else:
    sprint_path = os.path.join(hier, "BPMN")

bpmn_file = os.path.join(sprint_path, "G7_Rechnungsfreigabe.bpmn")
forms_dir = os.path.join(sprint_path, "Forms")

print(f"[Deploy] Verwende Plattform: '{plattform}'")
print(f"[Deploy] Lade BPMN aus: {bpmn_file}")
print(f"[Deploy] Lade Forms aus: {forms_dir}")

RESSOURCEN = [
    bpmn_file,
    os.path.join(forms_dir, "compliance-regeln.dmn"),
    os.path.join(forms_dir, "Compliance_Check.form"),
    os.path.join(forms_dir, "ERP_Bestaetigung.form"),
    os.path.join(forms_dir, "Manuelle_Speicherung.form"),
    os.path.join(forms_dir, "Manuelle_Zahlung.form"),
    os.path.join(forms_dir, "Metadaten_Erfassung.form"),
    os.path.join(forms_dir, "Portal_Start.form"),
    os.path.join(forms_dir, "Rechnungs_Pruefung.form"),
    os.path.join(forms_dir, "Rueckfrage.form"),
]


async def main() -> None:
    # Überprüfen, ob alle Dateien existieren
    for res in RESSOURCEN:
        if not os.path.exists(res):
            print(f"[Deploy] Fehler: Datei existiert nicht: {res}")
            sys.exit(1)

    kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
    client = ZeebeClient(kanal)
    antwort = await client.deploy_resource(*RESSOURCEN)
    for d in antwort.deployments:
        print(d)


if __name__ == "__main__":
    asyncio.run(main())
