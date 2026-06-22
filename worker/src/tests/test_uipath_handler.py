"""Tests fuer handlers.uipath_handler."""
import pytest
from pyzeebe.errors import BusinessError

from handlers.uipath_handler import (
    ERROR_CODE_UIPATH,
    handle_uipath_erp_erfassung,
)


def beispiel_variablen() -> dict:
    return {
        "invoiceId": "INV-2026-B01",
        "invoiceNumber": "RE-2026-B01",
        "supplierName": "Mustermann GmbH",
        "invoiceDate": "2026-06-01",
        "dueDate": "2026-06-15",
        "amountNet": 840.34,
        "amountGross": 1000.00,
        "currency": "EUR",
        "iban": "DE12456789900987654",
        "fileName": "rechnung.pdf",
    }


@pytest.mark.asyncio
async def test_uipath_happy_path_gibt_erp_entered_zurueck():
    variablen = beispiel_variablen()
    variablen["simulateUiPathError"] = False
    
    ergebnis = await handle_uipath_erp_erfassung(**variablen)
    
    assert ergebnis["erpEntered"] is True
    assert ergebnis["uipathStatus"] == "SUCCESS"
    assert ergebnis["uipathRobotName"] == "UiPath-Bot-Sprint5 (Simuliert)"


@pytest.mark.asyncio
async def test_uipath_fehler_simuliert_wirft_business_error():
    variablen = beispiel_variablen()
    variablen["simulateUiPathError"] = True
    
    with pytest.raises(BusinessError) as info:
        await handle_uipath_erp_erfassung(**variablen)
        
    assert info.value.error_code == ERROR_CODE_UIPATH
    assert "ERP-Speicherung fehlgeschlagen" in str(info.value)
