import sqlite3
import aiosqlite
from datetime import datetime, timedelta


async def init_db(conn: aiosqlite.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS glucose_readings (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp         TEXT NOT NULL UNIQUE,
            value_mgdl        INTEGER NOT NULL,
            trend_arrow       INTEGER,
            is_high           INTEGER DEFAULT 0,
            is_low            INTEGER DEFAULT 0,
            measurement_color INTEGER
        )
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_timestamp ON glucose_readings(timestamp)"
    )
    await init_user_settings(conn)
    await init_alerts_table(conn)
    await init_telegram_recipients_table(conn)
    await _migrate_user_settings_columns(conn)
    await _migrate_alerts_columns(conn)
    await conn.commit()


async def init_user_settings(conn: aiosqlite.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id          INTEGER PRIMARY KEY,
            target_low  INTEGER NOT NULL,
            target_high INTEGER NOT NULL
        )
    """)


async def init_alerts_table(conn: aiosqlite.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at       TEXT NOT NULL,
            triggered_value  INTEGER NOT NULL,
            projected_value  INTEGER NOT NULL,
            minutes_to_hypo  REAL NOT NULL,
            slope            REAL NOT NULL,
            confidence       TEXT NOT NULL CHECK (confidence IN ('high', 'normal', 'low')),
            trend_arrow      INTEGER,
            status           TEXT NOT NULL DEFAULT 'active'
                             CHECK (status IN ('active', 'resolved', 'expired')),
            resolved_at      TEXT,
            telegram_sent    INTEGER DEFAULT 0,
            feedback         TEXT CHECK (feedback IN ('accurate', 'false_alarm') OR feedback IS NULL)
        )
    """)
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)")


async def init_telegram_recipients_table(conn: aiosqlite.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS telegram_recipients (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    TEXT NOT NULL UNIQUE,
            label      TEXT NOT NULL,
            enabled    INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)


async def _migrate_user_settings_columns(conn: aiosqlite.Connection) -> None:
    migrations = [
        "ALTER TABLE user_settings ADD COLUMN predictor_enabled INTEGER DEFAULT 1",
        "ALTER TABLE user_settings ADD COLUMN prediction_window_minutes INTEGER DEFAULT 20",
        "ALTER TABLE user_settings ADD COLUMN lookback_minutes INTEGER DEFAULT 20",
        "ALTER TABLE user_settings ADD COLUMN min_readings INTEGER DEFAULT 5",
        "ALTER TABLE user_settings ADD COLUMN alert_cooldown_minutes INTEGER DEFAULT 10",
        "ALTER TABLE user_settings ADD COLUMN telegram_bot_token TEXT",
        "ALTER TABLE user_settings ADD COLUMN telegram_last_update_id INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            await conn.execute(sql)
        except sqlite3.OperationalError:
            pass


async def _migrate_alerts_columns(conn: aiosqlite.Connection) -> None:
    try:
        await conn.execute(
            "ALTER TABLE alerts ADD COLUMN alert_type TEXT NOT NULL DEFAULT 'hypo'"
        )
    except sqlite3.OperationalError:
        pass


async def get_settings(conn: aiosqlite.Connection) -> dict | None:
    conn.row_factory = aiosqlite.Row
    async with conn.execute("""
        SELECT target_low, target_high, predictor_enabled, prediction_window_minutes,
               lookback_minutes, min_readings, alert_cooldown_minutes, telegram_bot_token,
               telegram_last_update_id
        FROM user_settings WHERE id = 1
    """) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def upsert_settings(conn: aiosqlite.Connection, target_low: int, target_high: int) -> dict:
    await conn.execute(
        "INSERT OR IGNORE INTO user_settings (id, target_low, target_high) VALUES (1, ?, ?)",
        (target_low, target_high),
    )
    await conn.execute(
        "UPDATE user_settings SET target_low=?, target_high=? WHERE id=1",
        (target_low, target_high),
    )
    await conn.commit()
    return {"target_low": target_low, "target_high": target_high}


async def patch_settings(conn: aiosqlite.Connection, **fields) -> None:
    if not fields:
        return
    await conn.execute(
        "INSERT OR IGNORE INTO user_settings (id, target_low, target_high) VALUES (1, 60, 140)"
    )
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await conn.execute(
        f"UPDATE user_settings SET {set_clause} WHERE id=1",
        list(fields.values()),
    )
    await conn.commit()


async def upsert_readings(conn: aiosqlite.Connection, readings: list[dict]) -> None:
    await conn.executemany(
        """
        INSERT OR IGNORE INTO glucose_readings
            (timestamp, value_mgdl, trend_arrow, is_high, is_low, measurement_color)
        VALUES
            (:timestamp, :value_mgdl, :trend_arrow, :is_high, :is_low, :measurement_color)
        """,
        readings,
    )
    await conn.commit()


async def get_latest(conn: aiosqlite.Connection) -> dict | None:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        "SELECT * FROM glucose_readings ORDER BY timestamp DESC LIMIT 1"
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def get_readings(
    conn: aiosqlite.Connection, from_dt: datetime, to_dt: datetime
) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        """
        SELECT * FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (from_dt.isoformat(), to_dt.isoformat()),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def get_time_in_range(
    conn: aiosqlite.Connection,
    from_dt: datetime,
    to_dt: datetime,
    low: int,
    high: int,
) -> dict:
    async with conn.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN value_mgdl BETWEEN ? AND ? THEN 1 ELSE 0 END) as in_range,
            SUM(CASE WHEN value_mgdl > ? THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN value_mgdl < ? THEN 1 ELSE 0 END) as low
        FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        """,
        (low, high, high, low, from_dt.isoformat(), to_dt.isoformat()),
    ) as cur:
        row = await cur.fetchone()
    total = row[0] or 1
    return {
        "total": row[0],
        "in_range_pct": round((row[1] or 0) / total * 100, 1),
        "high_pct": round((row[2] or 0) / total * 100, 1),
        "low_pct": round((row[3] or 0) / total * 100, 1),
    }


async def get_hourly_patterns(
    conn: aiosqlite.Connection, from_dt: datetime, to_dt: datetime
) -> list[dict]:
    async with conn.execute(
        """
        SELECT
            CAST(strftime('%H', timestamp) AS INTEGER) as hour,
            ROUND(AVG(value_mgdl), 1) as avg,
            MIN(value_mgdl) as min,
            MAX(value_mgdl) as max
        FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY hour
        ORDER BY hour
        """,
        (from_dt.isoformat(), to_dt.isoformat()),
    ) as cur:
        rows = await cur.fetchall()
    return [{"hour": r[0], "avg": r[1], "min": r[2], "max": r[3]} for r in rows]


async def get_events(
    conn: aiosqlite.Connection,
    from_dt: datetime,
    to_dt: datetime,
    low: int,
    high: int,
) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        """
        SELECT timestamp, value_mgdl FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (from_dt.isoformat(), to_dt.isoformat()),
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    events: list[dict] = []
    current: dict | None = None

    for r in rows:
        v = r["value_mgdl"]
        if v < low:
            etype = "hypo"
        elif v > high:
            etype = "hyper"
        else:
            if current:
                events.append(current)
                current = None
            continue

        if current and current["type"] == etype:
            current["ended_at"] = r["timestamp"]
            current["extreme"] = (
                min(current["extreme"], v) if etype == "hypo" else max(current["extreme"], v)
            )
        else:
            if current:
                events.append(current)
            current = {
                "type": etype,
                "started_at": r["timestamp"],
                "ended_at": r["timestamp"],
                "extreme": v,
            }

    if current:
        events.append(current)

    for e in events:
        start = datetime.fromisoformat(e["started_at"])
        end = datetime.fromisoformat(e["ended_at"])
        e["duration_min"] = max(5, int((end - start).total_seconds() / 60))

    return events


_OVERLAY_COLORS = [
    "#3b82f6", "#ef4444", "#10b981", "#f59e0b",
    "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
]


async def get_overlay_data(
    conn: aiosqlite.Connection,
    from_dt: datetime,
    to_dt: datetime,
    group_by: str,  # "day" | "week" | "month"
) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        """
        SELECT timestamp, value_mgdl FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (from_dt.isoformat(), to_dt.isoformat()),
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    series: dict[str, dict[int, list[int]]] = {}

    for r in rows:
        dt = datetime.fromisoformat(r["timestamp"])
        if group_by == "day":
            key = dt.strftime("%a %d/%m")
            x = dt.hour
        elif group_by == "week":
            week_num = (dt.date() - from_dt.date()).days // 7 + 1
            key = f"Semana {week_num}"
            x = dt.weekday()
        else:  # month
            key = dt.strftime("%b %Y")
            x = dt.day

        series.setdefault(key, {}).setdefault(x, []).append(r["value_mgdl"])

    result = []
    for i, (label, by_x) in enumerate(series.items()):
        averaged = [
            {"x": x, "value": round(sum(vals) / len(vals), 1)}
            for x, vals in sorted(by_x.items())
        ]
        result.append({
            "label": label,
            "color": _OVERLAY_COLORS[i % len(_OVERLAY_COLORS)],
            "data": averaged,
        })

    return result


# ── get_readings_since ─────────────────────────────────────────────────────────

async def get_readings_since(conn: aiosqlite.Connection, minutes: int) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        "SELECT timestamp FROM glucose_readings ORDER BY timestamp DESC LIMIT 1"
    ) as cur:
        latest = await cur.fetchone()
    if latest is None:
        return []

    latest_ts = latest["timestamp"]
    cutoff = (datetime.fromisoformat(latest_ts) - timedelta(minutes=minutes)).isoformat()
    async with conn.execute(
        """
        SELECT * FROM glucose_readings
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (cutoff, latest_ts),
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


# ── Alert CRUD ─────────────────────────────────────────────────────────────────

async def insert_alert(conn: aiosqlite.Connection, alert: dict) -> dict:
    data = {"alert_type": "hypo", **alert}
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        """
        INSERT INTO alerts
            (created_at, triggered_value, projected_value, minutes_to_hypo,
             slope, confidence, trend_arrow, telegram_sent, alert_type)
        VALUES
            (:created_at, :triggered_value, :projected_value, :minutes_to_hypo,
             :slope, :confidence, :trend_arrow, :telegram_sent, :alert_type)
        """,
        data,
    ) as cur:
        alert_id = cur.lastrowid
    await conn.commit()
    async with conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)) as cur:
        row = await cur.fetchone()
    return dict(row)


async def get_latest_active_alert(
    conn: aiosqlite.Connection, alert_type: str | None = None
) -> dict | None:
    conn.row_factory = aiosqlite.Row
    if alert_type:
        sql = "SELECT * FROM alerts WHERE status='active' AND alert_type=? ORDER BY created_at DESC LIMIT 1"
        params: tuple = (alert_type,)
    else:
        sql = "SELECT * FROM alerts WHERE status='active' ORDER BY created_at DESC LIMIT 1"
        params = ()
    async with conn.execute(sql, params) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def list_alerts(
    conn: aiosqlite.Connection,
    start: str | None = None,
    end: str | None = None,
    status: str | None = None,
    alert_type: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    where, params = [], []
    if start:
        where.append("created_at >= ?")
        params.append(start)
    if end:
        where.append("created_at <= ?")
        params.append(end)
    if status:
        where.append("status = ?")
        params.append(status)
    if alert_type:
        where.append("alert_type = ?")
        params.append(alert_type)
    sql = "SELECT * FROM alerts"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"
    async with conn.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_alert_status(
    conn: aiosqlite.Connection,
    alert_id: int,
    status: str,
    resolved_at: str | None = None,
) -> None:
    if resolved_at:
        await conn.execute(
            "UPDATE alerts SET status=?, resolved_at=? WHERE id=?",
            (status, resolved_at, alert_id),
        )
    else:
        await conn.execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))
    await conn.commit()


async def update_alert_feedback(
    conn: aiosqlite.Connection, alert_id: int, feedback: str
) -> dict | None:
    conn.row_factory = aiosqlite.Row
    await conn.execute("UPDATE alerts SET feedback=? WHERE id=?", (feedback, alert_id))
    await conn.commit()
    async with conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def update_alert_telegram_sent(
    conn: aiosqlite.Connection, alert_id: int, sent: bool
) -> None:
    await conn.execute(
        "UPDATE alerts SET telegram_sent=? WHERE id=?", (int(sent), alert_id)
    )
    await conn.commit()


async def get_alert_stats(
    conn: aiosqlite.Connection,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    where, params = [], []
    if start:
        where.append("created_at >= ?")
        params.append(start)
    if end:
        where.append("created_at <= ?")
        params.append(end)
    sql = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN feedback='accurate' THEN 1 ELSE 0 END) as accurate_count,
            SUM(CASE WHEN feedback='false_alarm' THEN 1 ELSE 0 END) as false_alarm_count,
            SUM(CASE WHEN feedback IS NULL THEN 1 ELSE 0 END) as feedback_pending_count
        FROM alerts
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    async with conn.execute(sql, params) as cur:
        row = await cur.fetchone()
    return {
        "total": row[0] or 0,
        "accurate_count": row[1] or 0,
        "false_alarm_count": row[2] or 0,
        "feedback_pending_count": row[3] or 0,
    }


# ── Telegram recipient CRUD ────────────────────────────────────────────────────

async def insert_recipient(
    conn: aiosqlite.Connection, chat_id: str, label: str, enabled: int = 1
) -> dict:
    conn.row_factory = aiosqlite.Row
    created_at = datetime.now().isoformat()
    async with conn.execute(
        "INSERT INTO telegram_recipients (chat_id, label, enabled, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, label, enabled, created_at),
    ) as cur:
        rid = cur.lastrowid
    await conn.commit()
    async with conn.execute("SELECT * FROM telegram_recipients WHERE id=?", (rid,)) as cur:
        row = await cur.fetchone()
    return dict(row)


async def list_recipients(conn: aiosqlite.Connection) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute("SELECT * FROM telegram_recipients ORDER BY id") as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def list_enabled_recipients(conn: aiosqlite.Connection) -> list[dict]:
    conn.row_factory = aiosqlite.Row
    async with conn.execute(
        "SELECT * FROM telegram_recipients WHERE enabled=1 ORDER BY id"
    ) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def update_recipient(
    conn: aiosqlite.Connection, rid: int, **fields
) -> dict | None:
    if not fields:
        return None
    conn.row_factory = aiosqlite.Row
    set_clause = ", ".join(f"{k}=?" for k in fields)
    await conn.execute(
        f"UPDATE telegram_recipients SET {set_clause} WHERE id=?",
        [*fields.values(), rid],
    )
    await conn.commit()
    async with conn.execute("SELECT * FROM telegram_recipients WHERE id=?", (rid,)) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def delete_recipient(conn: aiosqlite.Connection, rid: int) -> None:
    await conn.execute("DELETE FROM telegram_recipients WHERE id=?", (rid,))
    await conn.commit()
