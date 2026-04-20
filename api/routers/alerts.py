from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import aiosqlite

from api.config import settings as config_settings
from api import database, predictor

router = APIRouter(prefix="/alerts")


class FeedbackBody(BaseModel):
    feedback: str


@router.get("")
async def list_alerts(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int | None = Query(default=None),
) -> list[dict]:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        return await database.list_alerts(conn, start=start, end=end, status=status, limit=limit)


@router.get("/active")
async def get_active_alert() -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        alert = await database.get_latest_active_alert(conn)
        if alert is not None:
            settings = await database.get_settings(conn) or {
                "target_low": config_settings.target_low,
                "target_high": config_settings.target_high,
            }
            live = await predictor.get_live_projection(conn, settings, alert["alert_type"])
            if live is not None:
                alert = {**alert, **{f"live_{k}": v for k, v in live.items()}}
    if alert is None:
        raise HTTPException(status_code=404, detail="No active alert")
    return alert


@router.patch("/{alert_id}")
async def patch_feedback(alert_id: int, body: FeedbackBody) -> dict:
    if body.feedback not in ("accurate", "false_alarm"):
        raise HTTPException(status_code=400, detail="feedback must be 'accurate' or 'false_alarm'")
    async with aiosqlite.connect(config_settings.db_path) as conn:
        alert = await database.update_alert_feedback(conn, alert_id, body.feedback)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/stats")
async def get_stats(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        return await database.get_alert_stats(conn, start=start, end=end)
