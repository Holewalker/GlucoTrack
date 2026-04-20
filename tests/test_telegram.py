import pytest
import httpx
from unittest.mock import AsyncMock, patch
from api.telegram import send_alert, send_test, format_message


SAMPLE_ALERT = {
    "id": 1,
    "triggered_value": 78,
    "projected_value": 62,
    "minutes_to_hypo": 14.0,
    "confidence": "high",
}
SAMPLE_SETTINGS = {"prediction_window_minutes": 20}


def test_format_message_snapshot():
    msg = format_message(SAMPLE_ALERT, SAMPLE_SETTINGS)
    assert "78 mg/dL" in msg
    assert "62 mg/dL" in msg
    assert "14.0 min" in msg
    assert "alta" in msg


async def test_send_success_mocked():
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await send_alert("token123", "chat456", SAMPLE_ALERT, SAMPLE_SETTINGS)
    assert result is True


async def test_send_failure_returns_false():
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPStatusError(
        "500", request=httpx.Request("POST", "http://x"), response=httpx.Response(500)
    )):
        result = await send_alert("token123", "chat456", SAMPLE_ALERT, SAMPLE_SETTINGS)
    assert result is False


async def test_send_timeout_returns_false():
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("timeout")):
        result = await send_test("token123", "chat456")
    assert result is False
