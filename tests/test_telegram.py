import pytest
import httpx
from unittest.mock import AsyncMock, patch
from api.telegram import send_alert, send_test, send_status, format_message, format_status_message


SAMPLE_ALERT = {
    "id": 1,
    "triggered_value": 78,
    "projected_value": 62,
    "minutes_to_hypo": 14.0,
    "confidence": "high",
    "alert_type": "hypo",
}
SAMPLE_SETTINGS = {"prediction_window_minutes": 20}


def test_format_message_snapshot():
    msg = format_message(SAMPLE_ALERT, SAMPLE_SETTINGS)
    assert "78 mg/dL" in msg
    assert "62 mg/dL" in msg
    assert "Riesgo estimado en ~14 min" in msg
    assert "alta" in msg


def test_format_message_in_progress_hyper():
    msg = format_message(
        {
            "triggered_value": 217,
            "projected_value": 223,
            "minutes_to_hypo": 118.6,
            "confidence": "normal",
            "alert_type": "hyper",
        },
        {"prediction_window_minutes": 20, "target_high": 180},
    )
    assert "Hiperglucemia en curso" in msg
    assert "223 mg/dL" in msg
    assert "Riesgo estimado" not in msg


def test_format_status_message_risk_hyper():
    msg = format_status_message(
        {
            "timestamp": "2026-04-20T11:21:53",
            "current_value": 169,
            "trend_arrow": 4,
            "projected_value": 210,
            "minutes_to_hypo": 9.6,
            "confidence": "high",
            "alert_type": "hyper",
            "state": "risk",
            "window": 20,
        }
    )
    assert "169 mg/dL" in msg
    assert "↗" in msg
    assert "210 mg/dL" in msg
    assert "Riesgo de hiperglucemia" in msg


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


async def test_send_status_success_mocked():
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await send_status(
            "token123",
            "chat456",
            {
                "timestamp": "2026-04-20T11:21:53",
                "current_value": 217,
                "trend_arrow": 4,
                "projected_value": 246,
                "minutes_to_hypo": 0.0,
                "confidence": "normal",
                "alert_type": "hyper",
                "state": "in_progress",
                "window": 20,
            },
        )
    assert result is True
