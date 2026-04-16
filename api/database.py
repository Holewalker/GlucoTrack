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
