import asyncio
import logging
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api import database, poller
from api.routers import glucose, stats

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(settings.db_path) as conn:
        await database.init_db(conn)
    task = asyncio.create_task(poller.run_poller())
    yield
    task.cancel()


app = FastAPI(title="Glucose Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glucose.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
