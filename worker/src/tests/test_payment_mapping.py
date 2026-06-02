import pytest

from mapping.payment_mapping import MappingFehler, variablen_zu_zahlungsauftrag


def vollstaendige_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-099",
        "supplierName": "Beispiel AG",
        "iban": "DE12345678901234567890",
        "amountGross": 595.00,
        "currency": "EUR",
        # optional
        "supplierId": "SUP-456",
        "dueDate": "2026-05-10",
    }


def test_happy_path_liefert_alle_felder():
    auftrag = variablen_zu_zahlungsauftrag(vollstaendige_variablen())
    assert auftrag["invoiceId"] == "INV-2026-099"
    assert auftrag["supplierName"] == "Beispiel AG"
    assert auftrag["iban"] == "DE12345678901234567890"
    assert auftrag["amountGross"] == 595.00
    assert auftrag["currency"] == "EUR"
    assert auftrag["supplierId"] == "SUP-456"
    assert auftrag["dueDate"] == "2026-05-10"


def test_amount_wird_als_float_zurueckgegeben():
    auftrag = variablen_zu_zahlungsauftrag(vollstaendige_variablen())
    assert isinstance(auftrag["amountGross"], float)


def test_string_fuer_amount_wird_konvertiert():
    var = vollstaendige_variablen()
    var["amountGross"] = "1190.50"
    auftrag = variablen_zu_zahlungsauftrag(var)
    assert auftrag["amountGross"] == 1190.50


def test_fehlende_pflichtfelder():
    var = vollstaendige_variablen()
    del var["iban"]
    with pytest.raises(MappingFehler) as info:
        variablen_zu_zahlungsauftrag(var)
    assert "iban" in str(info.value)


def test_fehlender_betrag():
    var = vollstaendige_variablen()
    del var["amountGross"]
    with pytest.raises(MappingFehler, match="amountGross"):
        variablen_zu_zahlungsauftrag(var)


def test_optionale_felder_leer_wenn_nicht_vorhanden():
    var = vollstaendige_variablen()
    del var["supplierId"]
    del var["dueDate"]
    auftrag = variablen_zu_zahlungsauftrag(var)
    assert auftrag["supplierId"] == ""
    assert auftrag["dueDate"] == ""


def test_leerer_string_zaehlt_als_fehlend():
    var = vollstaendige_variablen()
    var["supplierName"] = "   "
    with pytest.raises(MappingFehler, match="supplierName"):
        variablen_zu_zahlungsauftrag(var)


def test_nicht_numerischer_betrag():
    var = vollstaendige_variablen()
    var["amountGross"] = "keine-zahl"
    with pytest.raises(MappingFehler, match="amountGross"):
        variablen_zu_zahlungsauftrag(var)


def test_betrag_null_oder_negativ():
    for wert in (0, -1.0, -100.00):
        var = vollstaendige_variablen()
        var["amountGross"] = wert
        with pytest.raises(MappingFehler, match="positiv"):
            variablen_zu_zahlungsauftrag(var)


def test_strings_werden_getrimmt():
    var = vollstaendige_variablen()
    var["invoiceId"] = "  INV-2026-099  "
    auftrag = variablen_zu_zahlungsauftrag(var)
    assert auftrag["invoiceId"] == "INV-2026-099"
