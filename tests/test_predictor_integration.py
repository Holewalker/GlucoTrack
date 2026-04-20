import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from api import database, predictor


def _ts(minutes_ago: int) -> str:
    return (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()


def _reading(minutes_ago: int, value: int, trend_arrow: int = 2) -> dict:
    return {
        "timestamp": _ts(minutes_ago),
        "value_mgdl": value,
        "trend_arrow": trend_arrow,
        "is_high": False,
        "is_low": value < 60,
        "measurement_color": 1,
    }


SETTINGS = {
    "target_low": 60,
    "target_high": 140,
    "predictor_enabled": 1,
    "prediction_window_minutes": 20,
    "lookback_minutes": 25,
    "min_readings": 5,
    "alert_cooldown_minutes": 10,
}


async def test_descent_triggers_alert_and_telegram_attempted(db):
    readings = [
        _reading(20, 100), _reading(15, 94), _reading(10, 88),
        _reading(5, 82), _reading(0, 76),
    ]
    await database.upsert_readings(db, readings)

    mock_resp = AsyncMock()
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        alert = await predictor.evaluate(db, SETTINGS)

    assert alert is not None
    assert alert["status"] == "active"
    assert alert["projected_value"] < SETTINGS["target_low"]
    assert alert["created_at"] == readings[-1]["timestamp"]

    stored = await database.get_latest_active_alert(db)
    assert stored is not None
    assert stored["id"] == alert["id"]


async def test_flat_readings_no_alert(db):
    readings = [
        _reading(20, 90, 3), _reading(15, 91, 3), _reading(10, 90, 3),
        _reading(5, 89, 3), _reading(0, 90, 3),
    ]
    await database.upsert_readings(db, readings)
    alert = await predictor.evaluate(db, SETTINGS)
    assert alert is None


async def test_ascent_triggers_hyper_alert(db):
    readings = [
        _reading(20, 100, 4), _reading(15, 108, 4), _reading(10, 116, 4),
        _reading(5, 124, 5), _reading(0, 132, 5),
    ]
    await database.upsert_readings(db, readings)

    with patch("httpx.AsyncClient.post", side_effect=Exception("no telegram")):
        alert = await predictor.evaluate(db, SETTINGS)

    assert alert is not None
    assert alert["alert_type"] == "hyper"
    assert alert["status"] == "active"
    assert alert["projected_value"] > SETTINGS["target_high"]


async def test_active_alert_resolves_on_stabilization(db):
    readings = [
        _reading(20, 100), _reading(15, 94), _reading(10, 88),
        _reading(5, 82), _reading(0, 76),
    ]
    await database.upsert_readings(db, readings)

    with patch("httpx.AsyncClient.post", side_effect=Exception("no telegram")):
        first_alert = await predictor.evaluate(db, SETTINGS)
    assert first_alert is not None

    # Now glucose is rising — should auto-resolve
    stable_readings = [
        _reading(4, 78, 4), _reading(3, 82, 4), _reading(2, 86, 4),
        _reading(1, 90, 5), _reading(0, 95, 5),
    ]
    await database.upsert_readings(db, stable_readings)
    second_alert = await predictor.evaluate(db, SETTINGS)
    assert second_alert is None

    resolved = await database.list_alerts(db, status="resolved")
    assert len(resolved) == 1
    assert resolved[0]["id"] == first_alert["id"]
    assert resolved[0]["resolved_at"] == stable_readings[-1]["timestamp"]


async def test_lookback_uses_latest_reading_window(db):
    readings = [
        _reading(130, 100, 3),
        _reading(125, 102, 3),
        _reading(120, 101, 3),
        _reading(20, 100, 4),
        _reading(15, 108, 4),
        _reading(10, 116, 4),
        _reading(5, 124, 5),
        _reading(0, 132, 5),
    ]
    await database.upsert_readings(db, readings)

    with patch("httpx.AsyncClient.post", side_effect=Exception("no telegram")):
        alert = await predictor.evaluate(db, SETTINGS)

    assert alert is not None
    assert alert["alert_type"] == "hyper"
