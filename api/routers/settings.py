from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aiosqlite

from api.config import settings as config_settings
from api import database

router = APIRouter()

_PREDICTOR_DEFAULTS = {
    "predictor_enabled": 1,
    "prediction_window_minutes": 20,
    "lookback_minutes": 20,
    "min_readings": 5,
    "alert_cooldown_minutes": 10,
}


def _build_response(row: dict | None) -> dict:
    if row is None:
        return {
            "target_low": config_settings.target_low,
            "target_high": config_settings.target_high,
            **_PREDICTOR_DEFAULTS,
            "telegram_bot_token_set": False,
        }
    return {
        "target_low": row["target_low"],
        "target_high": row["target_high"],
        "predictor_enabled": row.get("predictor_enabled", 1),
        "prediction_window_minutes": row.get("prediction_window_minutes", 20),
        "lookback_minutes": row.get("lookback_minutes", 20),
        "min_readings": row.get("min_readings", 5),
        "alert_cooldown_minutes": row.get("alert_cooldown_minutes", 10),
        "telegram_bot_token_set": bool(row.get("telegram_bot_token")),
    }


class SettingsPatch(BaseModel):
    target_low: int | None = None
    target_high: int | None = None
    predictor_enabled: int | None = None
    prediction_window_minutes: int | None = None
    lookback_minutes: int | None = None
    min_readings: int | None = None
    alert_cooldown_minutes: int | None = None
    telegram_bot_token: str | None = None


@router.get("/settings")
async def read_settings() -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        row = await database.get_settings(conn)
    return _build_response(row)


@router.patch("/settings")
async def update_settings(body: SettingsPatch) -> dict:
    async with aiosqlite.connect(config_settings.db_path) as conn:
        current = await database.get_settings(conn)

        # Validate threshold fields if provided
        low = body.target_low if body.target_low is not None else (
            current["target_low"] if current else config_settings.target_low
        )
        high = body.target_high if body.target_high is not None else (
            current["target_high"] if current else config_settings.target_high
        )
        if low <= 0 or high <= 0:
            raise HTTPException(status_code=422, detail="Los valores deben ser positivos")
        if low >= high:
            raise HTTPException(status_code=422, detail="target_low debe ser menor que target_high")

        # Build patch dict from only the provided fields
        patch: dict = {}
        if body.target_low is not None:
            patch["target_low"] = body.target_low
        if body.target_high is not None:
            patch["target_high"] = body.target_high
        if body.predictor_enabled is not None:
            patch["predictor_enabled"] = body.predictor_enabled
        if body.prediction_window_minutes is not None:
            patch["prediction_window_minutes"] = body.prediction_window_minutes
        if body.lookback_minutes is not None:
            patch["lookback_minutes"] = body.lookback_minutes
        if body.min_readings is not None:
            patch["min_readings"] = body.min_readings
        if body.alert_cooldown_minutes is not None:
            patch["alert_cooldown_minutes"] = body.alert_cooldown_minutes
        if body.telegram_bot_token is not None:
            patch["telegram_bot_token"] = body.telegram_bot_token

        await database.patch_settings(conn, **patch)
        row = await database.get_settings(conn)

    return _build_response(row)
