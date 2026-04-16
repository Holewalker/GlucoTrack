import pytest
from datetime import datetime
from api.database import upsert_readings, get_time_in_range, get_hourly_patterns, get_events


READINGS = [
    # 3am — hypo
    {"timestamp": "2026-04-14T03:00:00", "value_mgdl": 55, "trend_arrow": 2, "is_high": False, "is_low": True, "measurement_color": 3},
    {"timestamp": "2026-04-14T03:05:00", "value_mgdl": 52, "trend_arrow": 2, "is_high": False, "is_low": True, "measurement_color": 3},
    {"timestamp": "2026-04-14T03:10:00", "value_mgdl": 58, "trend_arrow": 3, "is_high": False, "is_low": True, "measurement_color": 3},
    # 8am — in range
    {"timestamp": "2026-04-14T08:00:00", "value_mgdl": 95, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
    {"timestamp": "2026-04-14T08:05:00", "value_mgdl": 100, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
    # 14pm — hyper
    {"timestamp": "2026-04-14T14:00:00", "value_mgdl": 185, "trend_arrow": 4, "is_high": True, "is_low": False, "measurement_color": 2},
    {"timestamp": "2026-04-14T14:05:00", "value_mgdl": 190, "trend_arrow": 4, "is_high": True, "is_low": False, "measurement_color": 2},
    {"timestamp": "2026-04-14T14:10:00", "value_mgdl": 175, "trend_arrow": 3, "is_high": True, "is_low": False, "measurement_color": 2},
]

FROM_DT = datetime(2026, 4, 14, 0, 0, 0)
TO_DT = datetime(2026, 4, 14, 23, 59, 59)


async def test_time_in_range(db):
    await upsert_readings(db, READINGS)
    result = await get_time_in_range(db, FROM_DT, TO_DT, low=60, high=140)
    assert result["total"] == 8
    assert result["in_range_pct"] == 25.0   # 2/8
    assert result["low_pct"] == 37.5        # 3/8
    assert result["high_pct"] == 37.5       # 3/8


async def test_hourly_patterns(db):
    await upsert_readings(db, READINGS)
    result = await get_hourly_patterns(db, FROM_DT, TO_DT)
    hours = {r["hour"]: r for r in result}
    assert hours[3]["avg"] == round((55 + 52 + 58) / 3, 1)
    assert hours[8]["min"] == 95
    assert hours[14]["max"] == 190


async def test_events_detects_hypo_and_hyper(db):
    await upsert_readings(db, READINGS)
    events = await get_events(db, FROM_DT, TO_DT, low=60, high=140)
    types = [e["type"] for e in events]
    assert "hypo" in types
    assert "hyper" in types


async def test_events_hypo_extreme_is_min(db):
    await upsert_readings(db, READINGS)
    events = await get_events(db, FROM_DT, TO_DT, low=60, high=140)
    hypo = next(e for e in events if e["type"] == "hypo")
    assert hypo["extreme"] == 52


async def test_events_hyper_extreme_is_max(db):
    await upsert_readings(db, READINGS)
    events = await get_events(db, FROM_DT, TO_DT, low=60, high=140)
    hyper = next(e for e in events if e["type"] == "hyper")
    assert hyper["extreme"] == 190


from api.database import get_overlay_data

OVERLAY_READINGS = [
    {"timestamp": "2026-04-14T08:00:00", "value_mgdl": 90, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
    {"timestamp": "2026-04-14T09:00:00", "value_mgdl": 100, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
    {"timestamp": "2026-04-15T08:00:00", "value_mgdl": 110, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
    {"timestamp": "2026-04-15T09:00:00", "value_mgdl": 120, "trend_arrow": 3, "is_high": False, "is_low": False, "measurement_color": 1},
]


async def test_overlay_by_day_returns_two_series(db):
    await upsert_readings(db, OVERLAY_READINGS)
    from_dt = datetime(2026, 4, 14, 0, 0, 0)
    to_dt = datetime(2026, 4, 15, 23, 59, 59)
    result = await get_overlay_data(db, from_dt, to_dt, group_by="day")
    assert len(result) == 2


async def test_overlay_series_have_label_color_data(db):
    await upsert_readings(db, OVERLAY_READINGS)
    from_dt = datetime(2026, 4, 14, 0, 0, 0)
    to_dt = datetime(2026, 4, 15, 23, 59, 59)
    result = await get_overlay_data(db, from_dt, to_dt, group_by="day")
    for series in result:
        assert "label" in series
        assert "color" in series
        assert "data" in series
        assert all("x" in p and "value" in p for p in series["data"])
