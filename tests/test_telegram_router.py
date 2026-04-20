import pytest
import httpx
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock
from api.main import app
from api import database
from api.config import settings as config_settings


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(config_settings, "db_path", db_file)
    async with aiosqlite.connect(db_file) as conn:
        await database.init_db(conn)
        await database.patch_settings(conn, telegram_bot_token="test-token")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_create_recipient(client):
    res = await client.post("/api/telegram/recipients", json={"chat_id": "123", "label": "Me"})
    assert res.status_code == 201
    data = res.json()
    assert data["chat_id"] == "123"
    assert data["label"] == "Me"


async def test_list_recipients(client):
    await client.post("/api/telegram/recipients", json={"chat_id": "111", "label": "A"})
    await client.post("/api/telegram/recipients", json={"chat_id": "222", "label": "B"})
    res = await client.get("/api/telegram/recipients")
    assert res.status_code == 200
    assert len(res.json()) == 2


async def test_update_recipient_enabled(client):
    create = await client.post("/api/telegram/recipients", json={"chat_id": "123", "label": "Me"})
    rid = create.json()["id"]
    res = await client.patch(f"/api/telegram/recipients/{rid}", json={"enabled": 0})
    assert res.status_code == 200
    assert res.json()["enabled"] == 0


async def test_delete_recipient(client):
    create = await client.post("/api/telegram/recipients", json={"chat_id": "123", "label": "Me"})
    rid = create.json()["id"]
    res = await client.delete(f"/api/telegram/recipients/{rid}")
    assert res.status_code == 204
    list_res = await client.get("/api/telegram/recipients")
    assert len(list_res.json()) == 0


async def test_detect_chat_id_mocked(client):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json.return_value = {
        "result": [
            {"message": {"chat": {"id": 999, "first_name": "Ana", "type": "private"}}}
        ]
    }

    async def _fake_get(*a, **kw):
        return mock_resp

    with patch("httpx.AsyncClient.get", side_effect=_fake_get):
        res = await client.post("/api/telegram/detect-chat-id")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["chat_id"] == "999"


async def test_send_test_all_recipients(client):
    await client.post("/api/telegram/recipients", json={"chat_id": "123", "label": "Me"})
    with patch("api.telegram._send_message", return_value=True):
        res = await client.post("/api/telegram/test")
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) == 1
    assert results[0]["sent"] is True
