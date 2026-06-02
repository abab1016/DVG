import asyncio
import os

from pyzeebe import ZeebeClient, create_insecure_channel

ZEEBE_ADRESSE = os.getenv("ZEEBE_ADRESSE", "localhost:26500")
SPRINT = r"C:\Users\abuba\Downloads\Sprint 4"
FORMS = os.path.join(SPRINT, "Forms")

RESSOURCEN = [
    os.path.join(SPRINT, "G7_Rechnungsfreigabe.bpmn"),
    os.path.join(FORMS, "compliance-regeln.dmn"),
    os.path.join(FORMS, "Compliance_Check.form"),
    os.path.join(FORMS, "ERP_Bestaetigung.form"),
    os.path.join(FORMS, "Manuelle_Speicherung.form"),
    os.path.join(FORMS, "Manuelle_Zahlung.form"),
    os.path.join(FORMS, "Metadaten_Erfassung.form"),
    os.path.join(FORMS, "Portal_Start.form"),
    os.path.join(FORMS, "Rechnungs_Pruefung.form"),
    os.path.join(FORMS, "Rueckfrage.form"),
]


async def main() -> None:
    kanal = create_insecure_channel(grpc_address=ZEEBE_ADRESSE)
    client = ZeebeClient(kanal)
    antwort = await client.deploy_resource(*RESSOURCEN)
    for d in antwort.deployments:
        print(d)


if __name__ == "__main__":
    asyncio.run(main())
