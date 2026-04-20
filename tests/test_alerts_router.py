import pytest
import httpx
import aiosqlite
from api.main import app
from api import database
from api.config import settings as config_settings


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


async def _insert_alert(tmp_path, monkeypatch, **overrides):
    db_file = str(tmp_path / "test.db")
    defaults = {
        "created_at": "2026-04-20T10:00:00",
        "triggered_value": 78,
        "projected_value": 62,
        "minutes_to_hypo": 14.0,
        "slope": -0.8,
        "confidence": "high",
        "trend_arrow": 2,
        "telegram_sent": 0,
    }
    defaults.update(overrides)
    async with aiosqlite.connect(db_file) as conn:
        await database.init_db(conn)
        return await database.insert_alert(conn, defaults)


async def test_get_alerts_by_range(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 78,
            "projected_value": 62, "minutes_to_hypo": 14.0, "slope": -0.8,
            "confidence": "high", "trend_arrow": 2, "telegram_sent": 0,
        })
    res = await client.get("/api/alerts?start=2026-04-20T00:00:00&end=2026-04-20T23:59:59")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["triggered_value"] == 78


async def test_get_active_alert_none(client):
    res = await client.get("/api/alerts/active")
    assert res.status_code == 404


async def test_get_active_alert_existing(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 78,
            "projected_value": 62, "minutes_to_hypo": 14.0, "slope": -0.8,
            "confidence": "high", "trend_arrow": 2, "telegram_sent": 0,
        })
    res = await client.get("/api/alerts/active")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "active"
    assert data["confidence"] == "high"


async def test_get_active_alert_includes_live_hyper_projection(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.upsert_settings(conn, 60, 140)
        await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 120,
            "projected_value": 150, "minutes_to_hypo": 8.0, "slope": 1.0,
            "confidence": "normal", "trend_arrow": 4, "telegram_sent": 0,
            "alert_type": "hyper",
        })
        await database.upsert_readings(conn, [
            {"timestamp": "2026-04-20T10:00:00", "value_mgdl": 100, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:05:00", "value_mgdl": 108, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:10:00", "value_mgdl": 116, "trend_arrow": 4, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:15:00", "value_mgdl": 124, "trend_arrow": 5, "is_high": False, "is_low": False, "measurement_color": 2},
            {"timestamp": "2026-04-20T10:20:00", "value_mgdl": 132, "trend_arrow": 5, "is_high": False, "is_low": False, "measurement_color": 2},
        ])
    res = await client.get("/api/alerts/active")
    assert res.status_code == 200
    data = res.json()
    assert data["projected_value"] == 150
    assert data["live_projected_value"] == 164
    assert data["live_confidence"] == "high"
    assert data["live_minutes_to_hypo"] == 5.0


async def test_get_active_alert_includes_live_hypo_projection(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        await database.upsert_settings(conn, 60, 140)
        await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 82,
            "projected_value": 62, "minutes_to_hypo": 10.0, "slope": -0.8,
            "confidence": "normal", "trend_arrow": 3, "telegram_sent": 0,
            "alert_type": "hypo",
        })
        await database.upsert_readings(conn, [
            {"timestamp": "2026-04-20T10:00:00", "value_mgdl": 100, "trend_arrow": 2, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:05:00", "value_mgdl": 94, "trend_arrow": 2, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:10:00", "value_mgdl": 88, "trend_arrow": 2, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:15:00", "value_mgdl": 82, "trend_arrow": 2, "is_high": False, "is_low": False, "measurement_color": 1},
            {"timestamp": "2026-04-20T10:20:00", "value_mgdl": 76, "trend_arrow": 2, "is_high": False, "is_low": False, "measurement_color": 1},
        ])
    res = await client.get("/api/alerts/active")
    assert res.status_code == 200
    data = res.json()
    assert data["projected_value"] == 62
    assert data["live_projected_value"] == 52
    assert data["live_confidence"] == "high"
    assert data["live_minutes_to_hypo"] == 13.3


async def test_patch_feedback_accurate(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        alert = await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 78,
            "projected_value": 62, "minutes_to_hypo": 14.0, "slope": -0.8,
            "confidence": "high", "trend_arrow": 2, "telegram_sent": 0,
        })
    res = await client.patch(f"/api/alerts/{alert['id']}", json={"feedback": "accurate"})
    assert res.status_code == 200
    assert res.json()["feedback"] == "accurate"


async def test_patch_feedback_invalid_value_400(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        alert = await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 78,
            "projected_value": 62, "minutes_to_hypo": 14.0, "slope": -0.8,
            "confidence": "high", "trend_arrow": 2, "telegram_sent": 0,
        })
    res = await client.patch(f"/api/alerts/{alert['id']}", json={"feedback": "wrong"})
    assert res.status_code == 400


async def test_stats_aggregation(client, tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    async with aiosqlite.connect(db_file) as conn:
        a1 = await database.insert_alert(conn, {
            "created_at": "2026-04-20T10:00:00", "triggered_value": 78,
            "projected_value": 62, "minutes_to_hypo": 14.0, "slope": -0.8,
            "confidence": "high", "trend_arrow": 2, "telegram_sent": 0,
        })
        await database.update_alert_feedback(conn, a1["id"], "accurate")
        await database.insert_alert(conn, {
            "created_at": "2026-04-20T11:00:00", "triggered_value": 75,
            "projected_value": 58, "minutes_to_hypo": 10.0, "slope": -0.9,
            "confidence": "normal", "trend_arrow": 4, "telegram_sent": 0,
        })
    res = await client.get("/api/alerts/stats?start=2026-04-20T00:00:00&end=2026-04-20T23:59:59")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["accurate_count"] == 1
    assert data["feedback_pending_count"] == 1
