from unittest.mock import AsyncMock, patch

from api import database, poller
from api.poller import parse_reading


def test_parse_reading_formats_timestamp():
    raw = {
        "Timestamp": "4/14/2026 8:05:00 AM",
        "ValueInMgPerDl": 95,
        "TrendArrow": 3,
        "isHigh": False,
        "isLow": False,
        "MeasurementColor": 1,
    }
    result = parse_reading(raw)
    assert result["timestamp"] == "2026-04-14T08:05:00"
    assert result["value_mgdl"] == 95
    assert result["trend_arrow"] == 3
    assert result["is_high"] is False
    assert result["is_low"] is False


def test_parse_reading_pm_time():
    raw = {
        "Timestamp": "4/14/2026 2:30:00 PM",
        "ValueInMgPerDl": 150,
        "TrendArrow": 4,
        "isHigh": True,
        "isLow": False,
        "MeasurementColor": 2,
    }
    result = parse_reading(raw)
    assert result["timestamp"] == "2026-04-14T14:30:00"


async def test_process_telegram_status_command(db):
    await database.patch_settings(
        db,
        telegram_bot_token="token",
        telegram_last_update_id=0,
        target_low=60,
        target_high=140,
        prediction_window_minutes=20,
        lookback_minutes=20,
        min_readings=5,
    )
    await database.insert_recipient(db, "123", "Me", 1)
    await database.upsert_readings(
        db,
        [
            {"timestamp": "2026-04-20T10:00:00", "value_mgdl": 100, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:05:00", "value_mgdl": 108, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:10:00", "value_mgdl": 116, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:15:00", "value_mgdl": 124, "trend_arrow": 5, "is_high": False, "is_low": False, "measurement_color": 2},
            {"timestamp": "2026-04-20T10:20:00", "value_mgdl": 132, "trend_arrow": 5, "is_high": False, "is_low": False, "measurement_color": 2},
        ],
    )

    with patch("api.telegram.get_updates", return_value=[{"update_id": 7, "message": {"text": "/status", "chat": {"id": 123}}}]), \
         patch("api.telegram.send_status", new=AsyncMock(return_value=True)) as send_status:
        handled = await poller.process_telegram_commands(db, await database.get_settings(db))

    assert handled == 1
    send_status.assert_awaited_once()
    settings = await database.get_settings(db)
    assert settings["telegram_last_update_id"] == 8
