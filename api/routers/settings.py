from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiosqlite

from api.config import settings as config_settings
from api import database

router = APIRouter()


class SettingsPatch(BaseModel):
    target_low: int | None = None
    target_high: int | None = None


@router.get("/settings")
async def read_settings() -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        row = await database.get_settings(conn)
    if row:
        return row
    return {"target_low": config_settings.target_low, "target_high": config_settings.target_high}


@router.patch("/settings")
async def update_settings(body: SettingsPatch) -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        current = await database.get_settings(conn)
        low = body.target_low if body.target_low is not None else (current["target_low"] if current else config_settings.target_low)
        high = body.target_high if body.target_high is not None else (current["target_high"] if current else config_settings.target_high)

        if low <= 0 or high <= 0:
            raise HTTPException(status_code=422, detail="Los valores deben ser positivos")
        if low >= high:
            raise HTTPException(status_code=422, detail="target_low debe ser menor que target_high")

        return await database.upsert_settings(conn, low, high)
