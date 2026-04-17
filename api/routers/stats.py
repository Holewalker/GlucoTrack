from datetime import datetime, timedelta
from fastapi import APIRouter, Query
import aiosqlite
from api.config import settings
from api import database

router = APIRouter(prefix="/stats")


def _defaults(from_dt, to_dt):
    now = datetime.utcnow()
    return from_dt or (now - timedelta(days=7)), to_dt or now


@router.get("/time-in-range")
async def time_in_range(
    from_dt: datetime = Query(default=None, alias="from"),
    to_dt: datetime = Query(default=None, alias="to"),
):
    from_dt, to_dt = _defaults(from_dt, to_dt)
    async with aiosqlite.connect(settings.db_path) as conn:
        db_settings = await database.get_settings(conn)
        low = db_settings["target_low"] if db_settings else settings.target_low
        high = db_settings["target_high"] if db_settings else settings.target_high
        return await database.get_time_in_range(conn, from_dt, to_dt, low, high)


@router.get("/hourly-patterns")
async def hourly_patterns(
    from_dt: datetime = Query(default=None, alias="from"),
    to_dt: datetime = Query(default=None, alias="to"),
):
    from_dt, to_dt = _defaults(from_dt, to_dt)
    async with aiosqlite.connect(settings.db_path) as conn:
        return await database.get_hourly_patterns(conn, from_dt, to_dt)


@router.get("/events")
async def events(
    from_dt: datetime = Query(default=None, alias="from"),
    to_dt: datetime = Query(default=None, alias="to"),
):
    from_dt, to_dt = _defaults(from_dt, to_dt)
    async with aiosqlite.connect(settings.db_path) as conn:
        db_settings = await database.get_settings(conn)
        low = db_settings["target_low"] if db_settings else settings.target_low
        high = db_settings["target_high"] if db_settings else settings.target_high
        return await database.get_events(conn, from_dt, to_dt, low, high)
