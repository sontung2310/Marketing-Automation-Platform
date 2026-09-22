from collections.abc import AsyncIterator

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.models import Competitor
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.competitors import CompetitorsRepository
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
    first = await seed_database(seed_test_database, load_seed_bundle())
    first_counts = {
        name: await seed_test_database[name].count_documents({})
        for name in ("companies", "competitors", "competitor_activities", "trends", "influencers")
    }
    second = await seed_database(seed_test_database, load_seed_bundle())
    second_counts = {
        name: await seed_test_database[name].count_documents({}) for name in first_counts
    }

    assert first.coverage.counts["competitor_activities"] == 45
    assert first_counts == second_counts
    assert second.collections["competitor_activities"].inserted == 0
    assert second.collections["competitor_activities"].total == 45


async def test_duplicate_provenance_with_different_id_updates_existing_record(
    seed_test_database: AsyncDatabase[Document],
) -> None:
    bundle = load_seed_bundle()
    await seed_database(seed_test_database, bundle)

    original = bundle.competitors[0]
    replacement_data = original.model_dump(by_alias=True, mode="python")
    replacement_data.update({"_id": "cpt_replacement", "name": "Updated competitor"})
    replacement = Competitor.model_validate(replacement_data)

    result = await CompetitorsRepository(seed_test_database).upsert_by_source(replacement)

    assert result.inserted is False
    assert result.updated is True
    assert await seed_test_database["competitors"].count_documents({}) == len(bundle.competitors)
    stored = await seed_test_database["competitors"].find_one(
        {"source.system": original.source.system, "source.ref_id": original.source.ref_id}
    )
    assert stored is not None
    assert stored["_id"] == original.id
    assert stored["name"] == "Updated competitor"
