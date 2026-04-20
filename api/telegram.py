import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
TREND_SYMBOLS = {
    1: "↓↓",
    2: "↘",
    3: "→",
    4: "↗",
    5: "↑↑",
}


def _confidence_label(value: str | None) -> str:
    conf_map = {"high": "alta", "normal": "normal", "low": "baja"}
    if value is None:
        return "n/d"
    return conf_map.get(value, value)


def _is_in_progress(alert: dict, settings: dict) -> bool:
    alert_type = alert.get("alert_type", "hypo")
    threshold = settings.get("target_low", 60) if alert_type == "hypo" else settings.get("target_high", 140)
    current = alert.get("triggered_value", 0)
    return current <= threshold if alert_type == "hypo" else current >= threshold


def format_message(alert: dict, settings: dict) -> str:
    window = settings.get("prediction_window_minutes", 20)
    confidence_label = _confidence_label(alert.get("confidence"))
    alert_type = alert.get("alert_type", "hypo")
    in_progress = _is_in_progress(alert, settings)

    if alert_type == "hyper":
        if in_progress:
            return (
                f"⚠️ <b>Hiperglucemia en curso</b>\n\n"
                f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
                f"📈 Proyección a {window} min: {alert['projected_value']} mg/dL\n"
                f"📊 Confianza: {confidence_label}\n\n"
                f"💡 Considerá aplicar corrección."
            )
        return (
            f"⚠️ <b>Riesgo de hiperglucemia</b>\n\n"
            f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
            f"📈 Proyección a {window} min: {alert['projected_value']} mg/dL\n"
            f"⏱ Riesgo estimado en ~{round(alert['minutes_to_hypo'])} min\n"
            f"📊 Confianza: {confidence_label}\n\n"
            f"💡 Considerá aplicar corrección."
        )
    if in_progress:
        return (
            f"⚠️ <b>Hipoglucemia en curso</b>\n\n"
            f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
            f"📉 Proyección a {window} min: {alert['projected_value']} mg/dL\n"
            f"📊 Confianza: {confidence_label}\n\n"
            f"💡 Considerá comer algo con carbohidratos rápidos."
        )
    return (
        f"⚠️ <b>Riesgo de hipoglucemia</b>\n\n"
        f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
        f"📉 Proyección a {window} min: {alert['projected_value']} mg/dL\n"
        f"⏱ Riesgo estimado en ~{round(alert['minutes_to_hypo'])} min\n"
        f"📊 Confianza: {confidence_label}\n\n"
        f"💡 Considerá comer algo con carbohidratos rápidos."
    )


async def send_alert(
    bot_token: str, chat_id: str, alert: dict, settings: dict
) -> bool:
    text = format_message(alert, settings)
    return await _send_message(bot_token, chat_id, text)


async def send_test(bot_token: str, chat_id: str) -> bool:
    text = "✅ <b>Prueba de conexión</b>\n\nGlucoTrack está correctamente configurado."
    return await _send_message(bot_token, chat_id, text)


def format_status_message(status: dict) -> str:
    trend = TREND_SYMBOLS.get(status.get("trend_arrow"), "—")
    timestamp = datetime.fromisoformat(status["timestamp"]).strftime("%H:%M")
    lines = [
        "📊 <b>Estado actual</b>",
        "",
        f"🩸 Glucosa: {status['current_value']} mg/dL {trend}",
        f"🕒 Última lectura: {timestamp}",
    ]

    projected = status.get("projected_value")
    if projected is not None:
        lines.append(f"📈 Proyección a {status['window']} min: {projected} mg/dL")

    alert_type = status.get("alert_type")
    state = status.get("state")
    if state == "in_progress" and alert_type == "hyper":
        lines.append("🚨 Estado: hiperglucemia en curso")
    elif state == "in_progress" and alert_type == "hypo":
        lines.append("🚨 Estado: hipoglucemia en curso")
    elif state == "risk" and alert_type == "hyper":
        lines.append(f"⏱ Riesgo de hiperglucemia en ~{round(status['minutes_to_hypo'])} min")
    elif state == "risk" and alert_type == "hypo":
        lines.append(f"⏱ Riesgo de hipoglucemia en ~{round(status['minutes_to_hypo'])} min")
    elif state == "watch" and alert_type == "hyper":
        lines.append("👀 Tendencia alcista, sin riesgo inmediato")
    elif state == "watch" and alert_type == "hypo":
        lines.append("👀 Tendencia bajista, sin riesgo inmediato")
    else:
        lines.append("✅ Sin riesgo inmediato")

    if status.get("confidence") is not None:
        lines.append(f"📊 Confianza: {_confidence_label(status.get('confidence'))}")

    return "\n".join(lines)


async def send_status(bot_token: str, chat_id: str, status: dict) -> bool:
    return await _send_message(bot_token, chat_id, format_status_message(status))


async def _send_message(bot_token: str, chat_id: str, text: str) -> bool:
    url = TELEGRAM_API.format(token=bot_token, method="sendMessage")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Telegram send error to %s: %s", chat_id, exc)
        return False


async def detect_chat_id(bot_token: str) -> list[dict]:
    url = TELEGRAM_API.format(token=bot_token, method="getUpdates")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Telegram getUpdates error: %s", exc)
        return []

    seen: dict[str, dict] = {}
    for update in data.get("result", []):
        msg = update.get("message") or update.get("channel_post")
        if not msg:
            continue
        chat = msg.get("chat", {})
        chat_id = str(chat.get("id", ""))
        if not chat_id or chat_id in seen:
            continue
        name = (
            chat.get("title")
            or f"{chat.get('first_name', '')} {chat.get('last_name', '')}".strip()
            or chat_id
        )
        seen[chat_id] = {"chat_id": chat_id, "name": name, "type": chat.get("type", "")}

    return list(seen.values())


async def get_updates(bot_token: str, offset: int = 0) -> list[dict]:
    url = TELEGRAM_API.format(token=bot_token, method="getUpdates")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"offset": offset})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Telegram getUpdates error: %s", exc)
        return []

    return data.get("result", [])
