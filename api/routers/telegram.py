from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiosqlite

from api.config import settings as config_settings
from api import database, telegram as tg

router = APIRouter(prefix="/telegram")


class RecipientCreate(BaseModel):
    chat_id: str
    label: str
    enabled: int = 1


class RecipientPatch(BaseModel):
    label: str | None = None
    enabled: int | None = None


async def _get_bot_token(conn: aiosqlite.Connection) -> str:
    row = await database.get_settings(conn)
    token = row.get("telegram_bot_token") if row else None
    if not token:
        raise HTTPException(status_code=400, detail="telegram_bot_token no configurado")
    return token


@router.get("/recipients")
async def list_recipients() -> list[dict]:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        return await database.list_recipients(conn)


@router.post("/recipients", status_code=201)
async def create_recipient(body: RecipientCreate) -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        return await database.insert_recipient(conn, body.chat_id, body.label, body.enabled)


@router.patch("/recipients/{rid}")
async def update_recipient(rid: int, body: RecipientPatch) -> dict:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    async with aiosqlite.connect(config_settings.db_path) as conn:
        result = await database.update_recipient(conn, rid, **fields)
    if result is None:
        raise HTTPException(status_code=404, detail="Recipient not found")
    return result


@router.delete("/recipients/{rid}", status_code=204)
async def delete_recipient(rid: int) -> None:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        await database.delete_recipient(conn, rid)


@router.post("/detect-chat-id")
async def detect_chat_id() -> list[dict]:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        token = await _get_bot_token(conn)
    return await tg.detect_chat_id(token)


@router.post("/test")
async def send_test() -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        token = await _get_bot_token(conn)
        recipients = await database.list_enabled_recipients(conn)
    if not recipients:
        raise HTTPException(status_code=400, detail="No hay destinatarios habilitados")
    results = []
    for r in recipients:
        ok = await tg.send_test(token, r["chat_id"])
        results.append({"chat_id": r["chat_id"], "label": r["label"], "sent": ok})
    return {"results": results}
