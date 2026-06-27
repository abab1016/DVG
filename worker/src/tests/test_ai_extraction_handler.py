import json
import urllib.error
from unittest.mock import MagicMock, patch
import pytest
from pyzeebe.errors import BusinessError
from handlers.ai_extraction_handler import handle_ai_extraction


def mock_n8n_success_response():
    return json.dumps({
      "invoiceId": "INV-2026-140",
      "invoiceNumber": "RE-2026-140",
      "supplierName": "DVG Lieferant GmbH",
      "invoiceDate": "2026-06-20",
      "dueDate": "2026-07-20",
      "amountGross": 595.00,
      "amountNet": 500.00,
      "currency": "EUR",
      "iban": "DE89370400440532013000",
      "billingAddress": "Hauptstrasse 12, 12345 Berlin",
      "confidence": {
        "invoiceId": 0.95,
        "invoiceNumber": 0.98,
        "supplierName": 0.99,
        "invoiceDate": 0.97,
        "amountGross": 0.95,
        "currency": 0.99,
        "iban": 0.96,
        "billingAddress": 0.92
      },
      "sourceFile": "INV-2026-140.pdf",
      "extractionEngine": "n8n+gemini-1.5"
    })


@pytest.mark.asyncio
async def test_ai_extraction_handler_success():
    mock_response = MagicMock()
    mock_response.read.return_value = mock_n8n_success_response().encode("utf-8")
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        ergebnis = await handle_ai_extraction(fileName="beispiel_rechnung.pdf")

    mock_urlopen.assert_called_once()
    assert ergebnis["aiPlausibilityStatus"] == "VALID"
    assert ergebnis["invoiceId"] == "INV-2026-140"
    assert ergebnis["fileName"] == "INV-2026-140.pdf"
    assert ergebnis["channel"] == "EMAIL"
    assert ergebnis["aiReviewGruende"] == ""


@pytest.mark.asyncio
async def test_ai_extraction_handler_missing_filename():
    from handlers.ai_extraction_handler import ERROR_CODE_AI
    with pytest.raises(BusinessError) as info:
        await handle_ai_extraction()
    assert info.value.error_code == ERROR_CODE_AI


@pytest.mark.asyncio
async def test_ai_extraction_handler_connection_error():
    from handlers.ai_extraction_handler import ERROR_CODE_AI
    # Simulieren eines URLError
    error = urllib.error.URLError("Connection refused")
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(BusinessError) as info:
            await handle_ai_extraction(fileName="beispiel_rechnung.pdf")
    assert info.value.error_code == ERROR_CODE_AI
    assert "Connection refused" in str(info.value)


@pytest.mark.asyncio
async def test_ai_extraction_handler_unexpected_error():
    from handlers.ai_extraction_handler import ERROR_CODE_AI
    # Simulieren einer generischen Exception
    with patch("urllib.request.urlopen", side_effect=RuntimeError("Some crash")):
        with pytest.raises(BusinessError) as info:
            await handle_ai_extraction(fileName="beispiel_rechnung.pdf")
    assert info.value.error_code == ERROR_CODE_AI
    assert "Some crash" in str(info.value)
