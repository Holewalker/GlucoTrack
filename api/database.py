import aiosqlite
from datetime import datetime


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
