from collections.abc import AsyncIterator

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.core.db import Document
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.seed.writer import seed_database
from evals.runtime import throwaway_database


@pytest.fixture(autouse=True)
async def clear_mongo_client_between_event_loops() -> AsyncIterator[None]:
    """AsyncMongoClient is bound to one pytest event loop at a time."""

    yield
    if db.get_client.cache_info().currsize:
        await db.get_client().close()
        db.get_client.cache_clear()


@pytest.fixture
async def seeded_database() -> AsyncIterator[AsyncDatabase[Document]]:
    """A throwaway database holding the full mock seed, dropped afterwards."""

    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    async with throwaway_database("ma_seed") as database:
        await seed_database(database, load_seed_bundle())
        yield database
