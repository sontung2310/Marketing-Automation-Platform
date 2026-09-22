from collections.abc import AsyncIterator

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.repositories.base import Document
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.seed.writer import seed_database

pytestmark = pytest.mark.integration


@pytest.fixture
async def seed_test_database() -> AsyncIterator[AsyncDatabase[Document]]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    database_name = "marketing_automation_seed_test"
    database = db.get_client()[database_name]
    await db.get_client().drop_database(database_name)
    yield database
    await db.get_client().drop_database(database_name)
    await db.get_client().close()
    db.get_client.cache_clear()


async def test_seed_is_idempotent_and_meets_minimums(
    seed_test_database: AsyncDatabase[Document],
) -> None:
    bundle = load_seed_bundle()

    first = await seed_database(seed_test_database, bundle)
    first_counts = {
        name: await seed_test_database[name].count_documents({})
        for name in ("companies", "competitors", "competitor_activities", "trends", "influencers")
    }
    second = await seed_database(seed_test_database, bundle)
    second_counts = {
        name: await seed_test_database[name].count_documents({}) for name in first_counts
    }

    assert first.coverage.counts["competitor_activities"] == 45
    assert first_counts == second_counts
    assert second.collections["competitor_activities"].inserted == 0
    assert second.collections["competitor_activities"].skipped == 45
