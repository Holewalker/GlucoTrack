import pytest
import aiosqlite
from api.database import init_db


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await init_db(conn)
        yield conn
