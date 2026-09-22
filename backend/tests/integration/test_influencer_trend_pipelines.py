from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import pytest
from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.indexes import ensure_indexes
from app.pipelines.influencers import run_influencer_pipeline
from app.pipelines.sources.dct import DctSource
from app.pipelines.sources.pace import PaceSource
from app.pipelines.trends import run_trend_pipeline

pytestmark = pytest.mark.integration


@pytest.fixture
async def pipeline_databases() -> AsyncIterator[
    tuple[AsyncDatabase[Document], AsyncDatabase[Document], AsyncDatabase[Document]]
]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    source_name = "ma_influencer_trend_source"
    dct_name = "ma_dct_pipeline_owned"
    pace_name = "ma_pace_pipeline_owned"
    client = db.get_client()
    source_database = client[source_name]
    dct_database = client[dct_name]
    pace_database = client[pace_name]
    await client.drop_database(source_name)
    await client.drop_database(dct_name)
    await client.drop_database(pace_name)
    yield source_database, dct_database, pace_database
    await client.drop_database(source_name)
    await client.drop_database(dct_name)
    await client.drop_database(pace_name)
    await client.close()
    db.get_client.cache_clear()


async def test_dct_and_pace_pipelines_are_idempotent_and_source_safe(
    pipeline_databases: tuple[
        AsyncDatabase[Document], AsyncDatabase[Document], AsyncDatabase[Document]
    ],
) -> None:
    source_database, dct_database, pace_database = pipeline_databases
    dct_documents = [
        {
            "_id": ObjectId(),
            "company_id": "marketingeye.com.au",
            "platform": "x",
            "profile": {"display_name": f"Creator {index}", "followers": 1000 + index},
            "account": {
                "handle": f"creator{index}",
                "profile_url": f"https://x.example/creator{index}",
            },
            "evaluation": {
                "status": "eligible",
                "latest_final_score": 70 - index,
                "score_breakdown": {"topic_relevance": 5},
            },
            "platform_data": {
                "recent_posts": [
                    {
                        "text": f"Post {index}",
                        "url": f"https://x.example/creator{index}/post",
                        "likes": 10,
                        "replies": 2,
                        "reposts": 1,
                    }
                ]
            },
        }
        for index in range(26)
    ]
    await source_database["influencer_candidates"].insert_many(dct_documents)
    pace_documents = [
        {
            "_id": ObjectId(),
            "created_at": datetime(2026, 9, 20, tzinfo=UTC),
            "topics": ["Marketing"],
            "keywords": [{"term": "growth", "score": 0.8}],
            "source": "x_playwright",
            "title": f"Current {index}",
            "url": f"https://pace.example/current/{index}",
            "sentiment": {"label": "positive", "score": 0.5},
        }
        for index in range(25)
    ] + [
        {
            "_id": ObjectId(),
            "created_at": datetime(2026, 9, 10, tzinfo=UTC),
            "topics": ["Marketing"],
            "keywords": [{"term": "growth", "score": 0.6}],
            "source": "x_playwright",
            "title": f"Previous {index}",
            "url": f"https://pace.example/previous/{index}",
            "sentiment": {"label": "neutral", "score": 0.1},
        }
        for index in range(25)
    ]
    await source_database["ai_posts"].insert_many(pace_documents)
    source_counts_before = {
        name: await source_database[name].count_documents({})
        for name in ("influencer_candidates", "ai_posts")
    }
    await ensure_indexes(dct_database)
    await ensure_indexes(pace_database)

    first_influencers = await run_influencer_pipeline(DctSource(source_database), dct_database)
    second_influencers = await run_influencer_pipeline(DctSource(source_database), dct_database)
    first_trends = await run_trend_pipeline(
        PaceSource(source_database),
        pace_database,
        window_end_date=date(2026, 9, 22),
    )
    second_trends = await run_trend_pipeline(
        PaceSource(source_database),
        pace_database,
        window_end_date=date(2026, 9, 22),
    )

    assert first_influencers.influencers.inserted == 25
    assert second_influencers.influencers.inserted == 0
    assert await dct_database["influencers"].count_documents({}) == 25
    assert first_trends.used_seed_fallback is False
    assert first_trends.trends.inserted == 1
    assert second_trends.trends.inserted == 0
    assert await pace_database["trends"].count_documents({}) == 1
    trend = await pace_database["trends"].find_one({})
    assert trend is not None
    assert trend["mention_count"] == 25
    assert trend["direction"] == "STEADY"
    source_counts_after = {
        name: await source_database[name].count_documents({})
        for name in ("influencer_candidates", "ai_posts")
    }
    assert source_counts_after == source_counts_before
