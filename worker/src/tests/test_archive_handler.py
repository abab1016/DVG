"""Tests fuer handlers.archive_handler."""
import json
from unittest.mock import mock_open, patch

import pytest
from pyzeebe.errors import BusinessError

from handlers.archive_handler import (
    ERROR_CODE_ARCHIVE,
    _ARCHIV_ORDNER,
    handle_archivieren,
)


def vollstaendige_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-099",
        "metadataStored": True,
        "paymentRequested": True,
    }


@pytest.mark.asyncio
async def test_happy_path_gibt_archive_status_zurueck():
    with patch("handlers.archive_handler._datei_schreiben"):
        ergebnis = await handle_archivieren(**vollstaendige_variablen())

    assert ergebnis == {"archiveStatus": "DONE"}


@pytest.mark.asyncio
async def test_abschluss_json_enthaelt_korrekte_felder():
    geschrieben = {}

    def fake_schreiben(pfad, content):
        pfad.parent.mkdir(parents=True, exist_ok=True)
        geschrieben["content"] = content

    with patch("handlers.archive_handler._datei_schreiben", side_effect=fake_schreiben):
        await handle_archivieren(**vollstaendige_variablen())

    daten = json.loads(geschrieben["content"])
    assert daten["invoiceId"] == "INV-2026-099"
    assert daten["status"] == "ABGESCHLOSSEN"
    assert daten["metadataStored"] is True
    assert daten["paymentRequested"] is True
    assert "zeitpunkt" in daten


@pytest.mark.asyncio
async def test_dateiname_enthalt_abschluss_suffix():
    mock_f = mock_open()
    with patch("pathlib.Path.mkdir"):
        with patch("builtins.open", mock_f):
            await handle_archivieren(**vollstaendige_variablen())

    erwartet = _ARCHIV_ORDNER / "INV-2026-099_abschluss.json"
    mock_f.assert_called_once()
    aufruf_pfad = mock_f.call_args.args[0]
    assert aufruf_pfad == erwartet


@pytest.mark.asyncio
async def test_fehlt_invoice_id_wirft_business_error():
    variablen = {"metadataStored": True}
    with pytest.raises(BusinessError) as info:
        await handle_archivieren(**variablen)

    assert info.value.error_code == ERROR_CODE_ARCHIVE


@pytest.mark.asyncio
async def test_leere_invoice_id_wirft_business_error():
    variablen = {"invoiceId": "   "}
    with pytest.raises(BusinessError) as info:
        await handle_archivieren(**variablen)

    assert info.value.error_code == ERROR_CODE_ARCHIVE


@pytest.mark.asyncio
async def test_oserror_wird_re_raised():
    with patch("handlers.archive_handler._datei_schreiben",
               side_effect=OSError("Zugriff verweigert")):
        with pytest.raises(BusinessError) as info:
            await handle_archivieren(**vollstaendige_variablen())
    assert info.value.error_code == ERROR_CODE_ARCHIVE


@pytest.mark.asyncio
async def test_portal_upload_wird_als_beleg_pdf_archiviert():
    variablen = vollstaendige_variablen()
    variablen["pdfUpload"] = [{"documentId": "doc-1", "storeId": "local"}]
    geschrieben = {}

    def fake_schreiben(pfad, content):
        geschrieben["content"] = content

    with patch("handlers.archive_handler._datei_schreiben", side_effect=fake_schreiben), \
         patch("handlers.archive_handler.speichere_upload",
               return_value="INV-2026-099.pdf") as mock_upload:
        ergebnis = await handle_archivieren(**variablen)

    assert ergebnis == {"archiveStatus": "DONE"}
    mock_upload.assert_called_once_with(variablen["pdfUpload"])
    daten = json.loads(geschrieben["content"])
    assert daten["belegPdf"] == "INV-2026-099.pdf"


@pytest.mark.asyncio
async def test_beleg_pdf_download_fehler_bricht_archivierung_nicht():
    """Best-effort: ein fehlgeschlagener Beleg-Download darf die Archivierung
    des Abschlussdatensatzes nicht verhindern."""
    variablen = vollstaendige_variablen()
    variablen["pdfUpload"] = [{"documentId": "doc-1", "storeId": "local"}]
    geschrieben = {}

    def fake_schreiben(pfad, content):
        geschrieben["content"] = content

    with patch("handlers.archive_handler._datei_schreiben", side_effect=fake_schreiben), \
         patch("handlers.archive_handler.speichere_upload",
               side_effect=OSError("REST nicht erreichbar")):
        ergebnis = await handle_archivieren(**variablen)

    assert ergebnis == {"archiveStatus": "DONE"}
    daten = json.loads(geschrieben["content"])
    assert daten["belegPdf"] == ""


@pytest.mark.asyncio
async def test_ohne_upload_bleibt_beleg_pdf_leer():
    geschrieben = {}

    def fake_schreiben(pfad, content):
        geschrieben["content"] = content

    with patch("handlers.archive_handler._datei_schreiben", side_effect=fake_schreiben):
        await handle_archivieren(**vollstaendige_variablen())

    daten = json.loads(geschrieben["content"])
    assert daten["belegPdf"] == ""
