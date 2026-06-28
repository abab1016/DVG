import pytest

from mapping.grpc_mapping import (
    PROTO_FELDER,
    MappingFehler,
    variablen_zu_rechnung,
)


def vollstaendige_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-099",
        "invoiceNumber": "RE-2026-099",
        "supplierName": "Beispiel AG",
        "invoiceDate": "2026-04-10",
        "amountGross": 595.00,
        "currency": "EUR",
        "channel": "EMAIL",
        "billingAddress": "Musterweg 1, 12345 Musterstadt",
        # optional
        "fileName": "rechnung_april.pdf",
        "dueDate": "2026-05-10",
        "iban": "DE12345678901234567890",
        "amountNet": 500.00,
        "invoiceItems": [
            {"description": "Item A", "quantity": 2.0, "unitPrice": 10.0, "totalPrice": 20.0}
        ]
    }


def test_happy_path_liefert_proto_felder():
    rechnung = variablen_zu_rechnung(vollstaendige_variablen())
    assert rechnung["invoiceId"] == "INV-2026-099"
    assert rechnung["amountGross"] == 595.00
    assert rechnung["billingAddress"] == "Musterweg 1, 12345 Musterstadt"
    assert len(rechnung["items"]) == 1
    assert rechnung["items"][0]["description"] == "Item A"


def test_ausgabe_enthaelt_nur_proto_feldnamen():
    """Regression: invoiceNumber/channel duerfen NICHT ins gRPC-Dict.

    Sonst crasht invoice_pb2.Rechnungsmetadaten(**rechnung) mit ValueError.
    """
    rechnung = variablen_zu_rechnung(vollstaendige_variablen())
    for schluessel in rechnung:
        assert schluessel in PROTO_FELDER, f"Fremdschluessel im gRPC-Dict: {schluessel}"
    assert "invoiceNumber" not in rechnung
    assert "channel" not in rechnung


def test_kann_echtes_proto_konstruieren():
    """Wenn die Proto-Stubs generiert sind: echte Konstruktion darf nicht crashen.

    Achtung: `items` ist ein repeated-Message-Feld und kann NICHT per **kwargs
    als Liste von Dicts übergeben werden. Muss wie in grpc_client.py separat
    mit .items.add() befüllt werden.
    """
    pb2 = pytest.importorskip("invoice_pb2")
    rechnung = variablen_zu_rechnung(vollstaendige_variablen())
    items = rechnung.pop("items", [])
    nachricht = pb2.Rechnungsmetadaten(**rechnung)
    for item in items:
        nachricht.items.add(
            description=item.get("description", ""),
            quantity=float(item.get("quantity", 0.0)),
            unitPrice=float(item.get("unitPrice", 0.0)),
            totalPrice=float(item.get("totalPrice", 0.0)),
        )
    assert nachricht.invoiceId == "INV-2026-099"


def test_abgeleitete_proto_felder_vorhanden():
    rechnung = variablen_zu_rechnung(vollstaendige_variablen())
    assert rechnung["supplierId"].startswith("SUP-")
    assert rechnung["status"] == "OPEN"
    assert "createdAt" in rechnung


def test_amount_net_abgeleitet_wenn_fehlt():
    variablen = vollstaendige_variablen()
    del variablen["amountNet"]
    rechnung = variablen_zu_rechnung(variablen)
    assert rechnung["amountNet"] == round(595.00 / 1.19, 2)


def test_fehlende_scope_pflichtfelder_werden_aufgelistet():
    variablen = vollstaendige_variablen()
    del variablen["invoiceNumber"]
    del variablen["channel"]
    with pytest.raises(MappingFehler) as info:
        variablen_zu_rechnung(variablen)
    nachricht = str(info.value)
    assert "invoiceNumber" in nachricht
    assert "channel" in nachricht


def test_leerer_string_zaehlt_als_fehlendes_feld():
    variablen = vollstaendige_variablen()
    variablen["supplierName"] = "   "
    with pytest.raises(MappingFehler, match="supplierName"):
        variablen_zu_rechnung(variablen)


def test_nicht_numerischer_betrag_wirft_fehler():
    variablen = vollstaendige_variablen()
    variablen["amountGross"] = "kein-betrag"
    with pytest.raises(MappingFehler, match="amountGross"):
        variablen_zu_rechnung(variablen)


def test_inf_und_nan_werden_abgelehnt():
    for wert in ("inf", "nan", float("inf"), float("nan")):
        variablen = vollstaendige_variablen()
        variablen["amountGross"] = wert
        with pytest.raises(MappingFehler):
            variablen_zu_rechnung(variablen)


def test_negativer_betrag_wird_abgelehnt():
    variablen = vollstaendige_variablen()
    variablen["amountNet"] = -10.0
    with pytest.raises(MappingFehler, match="negativ"):
        variablen_zu_rechnung(variablen)


def test_brutto_kleiner_netto_wird_abgelehnt():
    variablen = vollstaendige_variablen()
    variablen["amountNet"] = 1000.0
    variablen["amountGross"] = 500.0
    with pytest.raises(MappingFehler, match="amountGross"):
        variablen_zu_rechnung(variablen)


def test_strings_werden_getrimmt():
    variablen = vollstaendige_variablen()
    variablen["invoiceId"] = "  INV-2026-099  "
    rechnung = variablen_zu_rechnung(variablen)
    assert rechnung["invoiceId"] == "INV-2026-099"
