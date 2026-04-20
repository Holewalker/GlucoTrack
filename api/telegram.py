import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def format_message(alert: dict, settings: dict) -> str:
    window = settings.get("prediction_window_minutes", 20)
    conf_map = {"high": "alta", "normal": "normal", "low": "baja"}
    confidence_label = conf_map.get(alert["confidence"], alert["confidence"])
    alert_type = alert.get("alert_type", "hypo")

    if alert_type == "hyper":
        return (
            f"⚠️ <b>Alerta de hiperglucemia</b>\n\n"
            f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
            f"📈 Proyectada en {window} min: {alert['projected_value']} mg/dL\n"
            f"⏱ Tiempo estimado a hiper: {alert['minutes_to_hypo']} min\n"
            f"📊 Confianza: {confidence_label}\n\n"
            f"💡 Considerá aplicar corrección."
        )
    return (
        f"⚠️ <b>Alerta de hipoglucemia</b>\n\n"
        f"🩸 Glucosa actual: {alert['triggered_value']} mg/dL\n"
        f"📉 Proyectada en {window} min: {alert['projected_value']} mg/dL\n"
        f"⏱ Tiempo estimado a hipo: {alert['minutes_to_hypo']} min\n"
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
