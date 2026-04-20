import asyncio
import logging
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api import database, poller
from api.routers import glucose, stats, settings as settings_router, alerts, telegram as telegram_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(settings.db_path) as conn:
        await database.init_db(conn)
    task = asyncio.create_task(poller.run_poller())

    def _on_poller_done(t: asyncio.Task) -> None:
        if not t.cancelled() and t.exception() is not None:
            logger.error("Poller task died: %s", t.exception(), exc_info=t.exception())

    task.add_done_callback(_on_poller_done)
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Glucose Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glucose.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(telegram_router.router, prefix="/api")
