import asyncio
import logging
from datetime import datetime

import aiosqlite
import httpx

from api import database, libre_client
from api.libre_client import LibreViewError
from api.config import settings

logger = logging.getLogger(__name__)

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


async def poll_once() -> None:
    global _token, _account_id, _patient_id
    try:
        if not _token:
            _token, _account_id = await libre_client.authenticate(
                settings.libre_email, settings.libre_password
            )
        if not _patient_id:
            _patient_id = settings.libre_patient_id or await libre_client.get_patient_id(
                _token, _account_id
            )

        data = await libre_client.get_cgm_data(_token, _account_id, _patient_id)

        readings = [parse_reading(r) for r in data.get("graphData", [])]
        if data.get("glucoseMeasurement"):
            readings.append(parse_reading(data["glucoseMeasurement"]))

        async with aiosqlite.connect(settings.db_path) as conn:
            await database.upsert_readings(conn, readings)

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
        await poll_once()
        await asyncio.sleep(settings.poll_interval_minutes * 60)
