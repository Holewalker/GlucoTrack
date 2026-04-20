from datetime import datetime, timedelta
from fastapi import APIRouter, Query
import aiosqlite
from api.config import settings
from api import database

router = APIRouter(prefix="/glucose")


@router.get("/current")
async def current():
    async with aiosqlite.connect(settings.db_path) as conn:
        return await database.get_latest(conn)


@router.get("/history")
async def history(
    from_dt: datetime = Query(default=None, alias="from"),
    to_dt: datetime = Query(default=None, alias="to"),
    bin_minutes: int = Query(default=0, ge=0),
):
    now = datetime.utcnow()
    from_dt = from_dt or (now - timedelta(hours=24))
    to_dt = to_dt or now
    async with aiosqlite.connect(settings.db_path) as conn:
        if bin_minutes > 0:
            return await database.get_readings_sampled(conn, from_dt, to_dt, bin_minutes * 60)
        return await database.get_readings(conn, from_dt, to_dt)


@router.get("/overlay")
async def overlay(
    from_dt: datetime = Query(alias="from"),
    to_dt: datetime = Query(alias="to"),
    group_by: str = Query(default="day", pattern="^(day|week|month)$"),
):
    async with aiosqlite.connect(settings.db_path) as conn:
        return await database.get_overlay_data(conn, from_dt, to_dt, group_by)
