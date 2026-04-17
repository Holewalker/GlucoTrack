import pytest
import httpx
import aiosqlite
from api.main import app
from api import database
from api.config import settings as config_settings


READINGS = [
    {"timestamp": "2026-04-14T08:00:00", "value_mgdl": 95, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
    {"timestamp": "2026-04-14T08:05:00", "value_mgdl": 55, "trend_arrow": 2, "is_high": False, "is_low": True, "measurement_color": 3},
    {"timestamp": "2026-04-14T08:10:00", "value_mgdl": 185, "trend_arrow": 6, "is_high": True, "is_low": False, "measurement_color": 2},
]


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(config_settings, "db_path", db_file)
    async with aiosqlite.connect(db_file) as conn:
        await database.init_db(conn)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_get_settings_env_fallback(client):
    res = await client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["target_low"] == config_settings.target_low
    assert data["target_high"] == config_settings.target_high


async def test_get_settings_returns_db_row(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.upsert_settings(conn, 70, 160)
    res = await client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert data["target_low"] == 70
    assert data["target_high"] == 160


async def test_patch_persists_and_get_reflects(client):
    res = await client.patch("/api/settings", json={"target_low": 65, "target_high": 150})
    assert res.status_code == 200
    assert res.json() == {"target_low": 65, "target_high": 150}

    get_res = await client.get("/api/settings")
    assert get_res.json() == {"target_low": 65, "target_high": 150}


async def test_patch_partial_merges_with_current(client):
    await client.patch("/api/settings", json={"target_low": 65, "target_high": 150})
    res = await client.patch("/api/settings", json={"target_high": 160})
    assert res.status_code == 200
    assert res.json() == {"target_low": 65, "target_high": 160}


async def test_patch_low_ge_high_returns_422(client):
    res = await client.patch("/api/settings", json={"target_low": 150, "target_high": 100})
    assert res.status_code == 422


async def test_patch_negative_value_returns_422(client):
    res = await client.patch("/api/settings", json={"target_low": -10, "target_high": 140})
    assert res.status_code == 422


async def test_stats_use_updated_thresholds(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.upsert_readings(conn, READINGS)

    # with default thresholds (60/140): 55 is low, 185 is high, 95 is in-range → 1/3 in range
    res1 = await client.get("/api/stats/time-in-range?from=2026-04-14T00:00:00&to=2026-04-14T23:59:59")
    assert res1.status_code == 200
    assert res1.json()["in_range_pct"] == pytest.approx(33.3, abs=0.1)

    # raise target_high to 200: now 55 is low, 95 and 185 are in-range → 2/3 in range
    await client.patch("/api/settings", json={"target_low": 60, "target_high": 200})
    res2 = await client.get("/api/stats/time-in-range?from=2026-04-14T00:00:00&to=2026-04-14T23:59:59")
    assert res2.status_code == 200
    assert res2.json()["in_range_pct"] == pytest.approx(66.7, abs=0.1)
