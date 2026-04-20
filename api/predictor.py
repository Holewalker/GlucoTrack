import logging
from datetime import datetime

import aiosqlite

from api import database, telegram as tg

logger = logging.getLogger(__name__)

SLOPE_NOISE_FLOOR = -0.3  # mg/dL per minute — descent gate
SLOPE_CEILING     =  0.3  # mg/dL per minute — ascent gate


def linear_regression(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Return (slope, intercept) from (x, y) points. x in minutes, y in mg/dL."""
    n = len(points)
    if n < 2:
        return 0.0, 0.0
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_x2 = sum(p[0] * p[0] for p in points)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _get_confidence(trend_arrow: int | None, alert_type: str = "hypo") -> str:
    if alert_type == "hypo":
        if trend_arrow in (1, 2):
            return "high"
        if trend_arrow == 3:
            return "normal"
    else:  # hyper
        if trend_arrow in (4, 5):
            return "high"
        if trend_arrow == 3:
            return "normal"
    return "low"


def _minutes_to_threshold(
    current_value: float,
    slope: float,
    threshold: int,
    alert_type: str,
) -> float:
    already_crossed = (
        current_value <= threshold if alert_type == "hypo" else current_value >= threshold
    )
    if already_crossed or slope == 0:
        return 0.0
    return round(abs((threshold - current_value) / slope), 1)


def _trend_state(readings: list[dict]) -> tuple[float, float, int | None]:
    latest_ts = datetime.fromisoformat(readings[-1]["timestamp"])
    points = [
        ((datetime.fromisoformat(r["timestamp"]) - latest_ts).total_seconds() / 60, r["value_mgdl"])
        for r in readings
    ]
    slope, _ = linear_regression(points)
    current_value = readings[-1]["value_mgdl"]
    trend_arrow = readings[-1].get("trend_arrow")
    return current_value, slope, trend_arrow


def build_live_projection(
    *,
    alert_type: str,
    current_value: float,
    slope: float,
    trend_arrow: int | None,
    window: int,
    threshold: int,
) -> dict:
    return {
        "current_value": int(current_value),
        "projected_value": int(current_value + slope * window),
        "minutes_to_hypo": _minutes_to_threshold(current_value, slope, threshold, alert_type),
        "slope": round(slope, 4),
        "confidence": _get_confidence(trend_arrow, alert_type),
        "trend_arrow": trend_arrow,
    }


async def get_prediction_snapshot(conn: aiosqlite.Connection, s: dict) -> dict | None:
    lookback = s.get("lookback_minutes", 20)
    min_readings = s.get("min_readings", 5)
    window = s.get("prediction_window_minutes", 20)
    target_low = s.get("target_low", 60)
    target_high = s.get("target_high", 140)

    latest = await database.get_latest(conn)
    if latest is None:
        return None

    readings = await database.get_readings_since(conn, lookback)
    if len(readings) < min_readings:
        return {
            "timestamp": latest["timestamp"],
            "current_value": latest["value_mgdl"],
            "trend_arrow": latest.get("trend_arrow"),
            "projected_value": None,
            "minutes_to_hypo": None,
            "slope": None,
            "confidence": None,
            "alert_type": "hypo" if latest["value_mgdl"] <= target_low else "hyper" if latest["value_mgdl"] >= target_high else None,
            "state": "in_progress" if latest["value_mgdl"] <= target_low or latest["value_mgdl"] >= target_high else "stable",
            "window": window,
        }

    current_value, slope, trend_arrow = _trend_state(readings)
    projected = current_value + slope * window

    if current_value <= target_low:
        alert_type = "hypo"
        state = "in_progress"
    elif current_value >= target_high:
        alert_type = "hyper"
        state = "in_progress"
    elif slope < SLOPE_NOISE_FLOOR and projected < target_low:
        alert_type = "hypo"
        state = "risk"
    elif slope > SLOPE_CEILING and projected > target_high:
        alert_type = "hyper"
        state = "risk"
    elif slope < 0:
        alert_type = "hypo"
        state = "watch"
    elif slope > 0:
        alert_type = "hyper"
        state = "watch"
    else:
        alert_type = None
        state = "stable"

    confidence = _get_confidence(trend_arrow, alert_type) if alert_type else None
    minutes_to = None
    if alert_type == "hypo":
        minutes_to = _minutes_to_threshold(current_value, slope, target_low, alert_type)
    elif alert_type == "hyper":
        minutes_to = _minutes_to_threshold(current_value, slope, target_high, alert_type)

    return {
        "timestamp": readings[-1]["timestamp"],
        "current_value": int(current_value),
        "trend_arrow": trend_arrow,
        "projected_value": int(projected),
        "minutes_to_hypo": minutes_to,
        "slope": round(slope, 4),
        "confidence": confidence,
        "alert_type": alert_type,
        "state": state,
        "window": window,
    }


async def get_live_projection(
    conn: aiosqlite.Connection,
    s: dict,
    alert_type: str,
) -> dict | None:
    lookback = s.get("lookback_minutes", 20)
    min_readings = s.get("min_readings", 5)
    window = s.get("prediction_window_minutes", 20)
    target_low = s.get("target_low", 60)
    target_high = s.get("target_high", 140)

    readings = await database.get_readings_since(conn, lookback)
    if len(readings) < min_readings:
        return None

    current_value, slope, trend_arrow = _trend_state(readings)
    threshold = target_low if alert_type == "hypo" else target_high
    return build_live_projection(
        alert_type=alert_type,
        current_value=current_value,
        slope=slope,
        trend_arrow=trend_arrow,
        window=window,
        threshold=threshold,
    )


async def _maybe_fire(
    conn: aiosqlite.Connection,
    s: dict,
    alert_type: str,
    active,
    now: datetime,
    current_value: float,
    slope: float,
    trend_arrow,
    window: int,
    cooldown: int,
    threshold: int,
) -> dict | None:
    """Check cooldown and insert alert if clear. Returns alert dict or None."""
    if active:
        created = datetime.fromisoformat(active["created_at"])
        if (now - created).total_seconds() / 60 < cooldown:
            return None
    else:
        recent = await database.list_alerts(conn, alert_type=alert_type, limit=1)
        if recent:
            last = datetime.fromisoformat(recent[0]["created_at"])
            if (now - last).total_seconds() / 60 < cooldown:
                return None

    live_projection = build_live_projection(
        alert_type=alert_type,
        current_value=current_value,
        slope=slope,
        trend_arrow=trend_arrow,
        window=window,
        threshold=threshold,
    )

    alert_data = {
        "alert_type": alert_type,
        "created_at": now.isoformat(),
        "triggered_value": int(current_value),
        "projected_value": live_projection["projected_value"],
        "minutes_to_hypo": live_projection["minutes_to_hypo"],
        "slope": live_projection["slope"],
        "confidence": live_projection["confidence"],
        "trend_arrow": trend_arrow,
        "telegram_sent": 0,
    }
    return await database.insert_alert(conn, alert_data)


async def evaluate(conn: aiosqlite.Connection, s: dict) -> dict | None:
    """Run prediction pipeline for both hypo and hyper. Returns inserted alert or None."""
    if not s.get("predictor_enabled", 1):
        return None

    lookback  = s.get("lookback_minutes", 20)
    min_readings = s.get("min_readings", 5)
    window    = s.get("prediction_window_minutes", 20)
    cooldown  = s.get("alert_cooldown_minutes", 10)
    target_low  = s.get("target_low", 60)
    target_high = s.get("target_high", 140)

    readings = await database.get_readings_since(conn, lookback)
    if len(readings) < min_readings:
        return None

    now = datetime.fromisoformat(readings[-1]["timestamp"])

    # Fetch active alerts per type
    active_hypo  = await database.get_latest_active_alert(conn, alert_type="hypo")
    active_hyper = await database.get_latest_active_alert(conn, alert_type="hyper")

    # Expire stale active alerts before gate checks
    for active in (active_hypo, active_hyper):
        if active:
            created = datetime.fromisoformat(active["created_at"])
            if (now - created).total_seconds() / 60 > 2 * window:
                await database.update_alert_status(conn, active["id"], "expired")
                if active is active_hypo:
                    active_hypo = None
                else:
                    active_hyper = None

    current_value, slope, trend_arrow = _trend_state(readings)

    # Auto-resolve: hypo clears when rising or back above target_low + 10
    if active_hypo:
        if slope >= 0 or current_value > target_low + 10:
            await database.update_alert_status(
                conn, active_hypo["id"], "resolved", resolved_at=now.isoformat()
            )
            active_hypo = None

    # Auto-resolve: hyper clears when falling or back below target_high - 10
    if active_hyper:
        if slope <= 0 or current_value < target_high - 10:
            await database.update_alert_status(
                conn, active_hyper["id"], "resolved", resolved_at=now.isoformat()
            )
            active_hyper = None

    projected = current_value + slope * window
    new_alert = None

    # Hypo gate — slope descending past noise floor, projection below target_low
    if slope < SLOPE_NOISE_FLOOR and projected < target_low:
        new_alert = await _maybe_fire(
            conn, s, "hypo", active_hypo, now,
            current_value, slope, trend_arrow, window, cooldown, target_low,
        )

    # Hyper gate — slope ascending past ceiling, projection above target_high
    if new_alert is None and slope > SLOPE_CEILING and projected > target_high:
        new_alert = await _maybe_fire(
            conn, s, "hyper", active_hyper, now,
            current_value, slope, trend_arrow, window, cooldown, target_high,
        )

    if new_alert is None:
        return None

    # Fire Telegram for each enabled recipient — failures never block
    bot_token = s.get("telegram_bot_token")
    if bot_token:
        recipients = await database.list_enabled_recipients(conn)
        any_sent = False
        for r in recipients:
            ok = await tg.send_alert(bot_token, r["chat_id"], new_alert, s)
            if ok:
                any_sent = True
        if any_sent:
            await database.update_alert_telegram_sent(conn, new_alert["id"], True)
            new_alert["telegram_sent"] = 1

    return new_alert
