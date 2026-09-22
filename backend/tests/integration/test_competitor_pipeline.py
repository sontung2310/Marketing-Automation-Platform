from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.indexes import ensure_indexes
from app.pipelines.competitor_activity import run_competitor_activity_pipeline
from app.pipelines.sources.competitorscope import CompetitorScopeSource

pytestmark = pytest.mark.integration


@pytest.fixture
async def pipeline_databases() -> AsyncIterator[
    tuple[AsyncDatabase[Document], AsyncDatabase[Document]]
]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    source_name = "competitor_pipeline_source_test"
    owned_name = "ma_competitor_pipeline_owned"
    client = db.get_client()
    source_database = client[source_name]
    owned_database = client[owned_name]
    await client.drop_database(source_name)
    await client.drop_database(owned_name)
    yield source_database, owned_database
    await client.drop_database(source_name)
    await client.drop_database(owned_name)
    await client.close()
    db.get_client.cache_clear()


async def _all_documents(database: AsyncDatabase[Document], collection_name: str) -> list[Document]:
    return [document async for document in database[collection_name].find({})]


async def test_competitor_pipeline_normalizes_and_is_idempotent(
    pipeline_databases: tuple[AsyncDatabase[Document], AsyncDatabase[Document]],
) -> None:
    source_database, owned_database = pipeline_databases
    source_company_id = ObjectId()
    competitor_id = ObjectId()
    target_id = ObjectId()
    source_documents = {
        "companies": [{"_id": source_company_id, "name": "Marketing Eye"}],
        "competitors": [
            {
                "_id": competitor_id,
                "name": "Lyfe Marketing",
                "website_url": "https://www.lyfemarketing.com/",
                "company_id": source_company_id,
            },
            {
                "_id": ObjectId(),
                "name": "Brown Bag Marketing",
                "website_url": "https://brownbagmarketing.com/",
            },
        ],
        "monitoring_targets": [
            {
                "_id": target_id,
                "competitor_id": competitor_id,
                "url": "https://www.lyfemarketing.com/blog",
            }
        ],
        "changes": [
            {
                "_id": ObjectId(),
                "monitoring_target_id": target_id,
                "change_type": change_type,
                "summary": f"{change_type} summary",
                "narrative_summary": narrative_summary,
                "detected_url": detected_url,
                "detected_at": datetime(2026, 9, 22, tzinfo=UTC),
                "is_simulated": change_type == "PRICE_CHANGE",
            }
            for change_type, narrative_summary, detected_url in (
                ("NEW_BLOG", "New blog post", "https://www.lyfemarketing.com/blog/new"),
                ("NEW_PRODUCT", None, "https://www.lyfemarketing.com/products/new"),
                ("PRICE_CHANGE", "Pricing changed", None),
                ("PRODUCT_REMOVED", "Product removed", ""),
                ("UNKNOWN_CHANGE", "Should be skipped", "https://example.invalid/unknown"),
            )
        ],
    }
    for collection_name, documents in source_documents.items():
        await source_database[collection_name].insert_many(documents)
    source_before = {name: await _all_documents(source_database, name) for name in source_documents}
    await ensure_indexes(owned_database)
    fixed_ingested_at = datetime(2026, 9, 22, 12, tzinfo=UTC)

    first = await run_competitor_activity_pipeline(
        CompetitorScopeSource(source_database),
        owned_database,
        ingested_at=fixed_ingested_at,
    )
    second = await run_competitor_activity_pipeline(
        CompetitorScopeSource(source_database),
        owned_database,
        ingested_at=fixed_ingested_at,
    )

    assert first.activities.inserted == 4
    assert first.activities.skipped == 1
    assert second.activities.inserted == 0
    assert second.activities.skipped == 5
    assert await owned_database["competitors"].count_documents({}) == 1
    assert await owned_database["competitor_activities"].count_documents({}) == 4
    activities = await _all_documents(owned_database, "competitor_activities")
    assert {activity["activity_type"] for activity in activities} == {
        "NEW_BLOG",
        "NEW_PRODUCT",
        "PRICE_CHANGE",
        "PRODUCT_REMOVED",
    }
    assert all(activity["channel"] == "WEBSITE" for activity in activities)
    assert all(len(activity["title"]) <= 120 for activity in activities)
    assert any(activity["is_simulated"] for activity in activities)
    source_after = {name: await _all_documents(source_database, name) for name in source_documents}
    assert source_after == source_before
