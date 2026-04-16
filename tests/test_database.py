import pytest
import aiosqlite
from api.database import init_db, upsert_readings, get_latest, get_readings
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
