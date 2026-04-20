import asyncio
import logging
from datetime import datetime

import aiosqlite
import httpx

from api import database, libre_client, predictor, telegram as tg
from api.libre_client import LibreViewError
from api.config import settings

logger = logging.getLogger(__name__)
TELEGRAM_COMMAND_POLL_SECONDS = 15

_token: str | None = None
_account_id: str | None = None
_patient_id: str | None = None


def parse_reading(raw: dict) -> dict:
    dt = datetime.strptime(raw["Timestamp"], "%m/%d/%Y %I:%M:%S %p")
    return {
        "timestamp": dt.isoformat(),
        "value_mgdl": raw["ValueInMgPerDl"],
        "trend_arrow": raw.get("TrendArrow"),
        "is_high": raw.get("isHigh", False),
        "is_low": raw.get("isLow", False),
        "measurement_color": raw.get("MeasurementColor"),
    }


async def process_telegram_commands(conn: aiosqlite.Connection, s: dict) -> int:
    bot_token = s.get("telegram_bot_token")
    if not bot_token:
        return 0

    offset = int(s.get("telegram_last_update_id") or 0)
    updates = await tg.get_updates(bot_token, offset)
    if not updates:
        return 0

    recipients = await database.list_enabled_recipients(conn)
    enabled_chat_ids = {r["chat_id"] for r in recipients}
    max_offset = offset
    handled = 0

    for update in updates:
        max_offset = max(max_offset, int(update.get("update_id", 0)) + 1)
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            continue
        text = (msg.get("text") or "").strip()
        if not text.startswith("/"):
            continue

        command = text.split()[0].split("@")[0].lower()
        chat_id = str((msg.get("chat") or {}).get("id", ""))
        if chat_id not in enabled_chat_ids:
            continue

        if command == "/status":
            status = await predictor.get_prediction_snapshot(conn, s)
            if status is not None:
                await tg.send_status(bot_token, chat_id, status)
                handled += 1

    if max_offset != offset:
        await database.patch_settings(conn, telegram_last_update_id=max_offset)
    return handled


async def poll_once() -> None:
    global _token, _account_id, _patient_id
    try:
        if not _token:
            _token, _account_id = await libre_client.authenticate(
                settings.libre_email, settings.libre_password
            )
        connections = await libre_client.get_connections(_token, _account_id)
        connection = connections[0]
        if not _patient_id:
            _patient_id = settings.libre_patient_id or connection["patientId"]

        data = await libre_client.get_cgm_data(_token, _account_id, _patient_id)

        readings = [parse_reading(r) for r in data.get("graphData", [])]
        if data.get("glucoseMeasurement"):
            readings.append(parse_reading(data["glucoseMeasurement"]))
        # connections endpoint has the freshest current reading (updates every ~1 min)
        if connection.get("glucoseMeasurement"):
            readings.append(parse_reading(connection["glucoseMeasurement"]))

        async with aiosqlite.connect(settings.db_path) as conn:
            await database.upsert_readings(conn, readings)
            db_settings = await database.get_settings(conn)
            s = db_settings or {"target_low": settings.target_low, "target_high": settings.target_high}
            try:
                await predictor.evaluate(conn, s)
            except Exception as exc:
                logger.error("Predictor error: %s", exc)
            try:
                await process_telegram_commands(conn, s)
            except Exception as exc:
                logger.error("Telegram command error: %s", exc)

        logger.info("Polled %d readings", len(readings))

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            _token = None
            _account_id = None
        logger.error("Poll HTTP error: %s", exc)
    except LibreViewError as exc:
        if exc.status in (401, 920):
            _token = None
            _account_id = None
        logger.error("Poll LibreView error: %s", exc)
    except Exception as exc:
        logger.error("Poll error: %s", exc)


async def run_poller() -> None:
    while True:
        try:
            await poll_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Unexpected error in run_poller: %s", exc, exc_info=True)
        try:
            await asyncio.sleep(settings.poll_interval_minutes * 60)
        except asyncio.CancelledError:
            raise


async def run_telegram_poller() -> None:
    while True:
        try:
            async with aiosqlite.connect(settings.db_path) as conn:
                s = await database.get_settings(conn)
                if s is not None:
                    await process_telegram_commands(conn, s)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Unexpected error in run_telegram_poller: %s", exc, exc_info=True)
        try:
            await asyncio.sleep(TELEGRAM_COMMAND_POLL_SECONDS)
        except asyncio.CancelledError:
            raise
