import pytest
import aiosqlite
from api.database import (
    init_db,
    upsert_readings,
    get_latest,
    get_readings,
    get_readings_since,
    get_settings,
    upsert_settings,
)
from datetime import datetime


SAMPLE_READINGS = [
    {
        "timestamp": "2026-04-14T08:00:00",
        "value_mgdl": 95,
        "trend_arrow": 3,
        "is_high": False,
        "is_low": False,
        "measurement_color": 1,
    },
    {
        "timestamp": "2026-04-14T08:05:00",
        "value_mgdl": 102,
        "trend_arrow": 4,
        "is_high": False,
        "is_low": False,
        "measurement_color": 1,
    },
    {
        "timestamp": "2026-04-14T08:10:00",
        "value_mgdl": 55,
        "trend_arrow": 2,
        "is_high": False,
        "is_low": True,
        "measurement_color": 3,
    },
]


async def test_init_creates_table(db):
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='glucose_readings'"
    ) as cur:
        row = await cur.fetchone()
    assert row is not None


async def test_upsert_inserts_readings(db):
    await upsert_readings(db, SAMPLE_READINGS)
    async with db.execute("SELECT COUNT(*) FROM glucose_readings") as cur:
        count = (await cur.fetchone())[0]
    assert count == 3


async def test_upsert_deduplicates(db):
    await upsert_readings(db, SAMPLE_READINGS)
    await upsert_readings(db, SAMPLE_READINGS)
    async with db.execute("SELECT COUNT(*) FROM glucose_readings") as cur:
        count = (await cur.fetchone())[0]
    assert count == 3


async def test_get_latest(db):
    await upsert_readings(db, SAMPLE_READINGS)
    latest = await get_latest(db)
    assert latest["value_mgdl"] == 55
    assert latest["timestamp"] == "2026-04-14T08:10:00"


async def test_get_readings_range(db):
    await upsert_readings(db, SAMPLE_READINGS)
    from_dt = datetime(2026, 4, 14, 8, 0, 0)
    to_dt = datetime(2026, 4, 14, 8, 7, 0)
    results = await get_readings(db, from_dt, to_dt)
    assert len(results) == 2
    assert results[0]["value_mgdl"] == 95


async def test_get_readings_since_anchors_to_latest_timestamp(db):
    readings = [
        {
            "timestamp": "2000-01-01T10:00:00",
            "value_mgdl": 90,
            "trend_arrow": 3,
            "is_high": False,
            "is_low": False,
            "measurement_color": 1,
        },
        {
            "timestamp": "2000-01-01T10:05:00",
            "value_mgdl": 92,
            "trend_arrow": 3,
            "is_high": False,
            "is_low": False,
            "measurement_color": 1,
        },
        {
            "timestamp": "2000-01-01T10:10:00",
            "value_mgdl": 95,
            "trend_arrow": 4,
            "is_high": False,
            "is_low": False,
            "measurement_color": 1,
        },
    ]
    await upsert_readings(db, readings)

    results = await get_readings_since(db, 5)

    assert [r["timestamp"] for r in results] == [
        "2000-01-01T10:05:00",
        "2000-01-01T10:10:00",
    ]


async def test_get_settings_empty(db):
    result = await get_settings(db)
    assert result is None


async def test_upsert_settings_creates_row(db):
    result = await upsert_settings(db, 60, 140)
    assert result == {"target_low": 60, "target_high": 140}
    row = await get_settings(db)
    assert row["target_low"] == 60
    assert row["target_high"] == 140


async def test_upsert_settings_overwrites(db):
    await upsert_settings(db, 60, 140)
    result = await upsert_settings(db, 70, 160)
    assert result == {"target_low": 70, "target_high": 160}
    row = await get_settings(db)
    assert row["target_low"] == 70
    assert row["target_high"] == 160
