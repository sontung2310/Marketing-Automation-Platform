"""Step 6 read side against a real, seeded MongoDB (roadmap 6-A, 6-B)."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.api.main import create_app
from app.core import db
from app.core.config import get_settings
from app.intelligence.startup import ensure_owned_indexes
from app.orchestration import feed
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.seed.writer import seed_database

pytestmark = pytest.mark.integration

DATABASE = "marketing_automation_api_test"
EXECUTION_TYPES = {"NEW_BLOG", "SOCIAL_POST", "EXECUTIVE_POST"}


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    monkeypatch.setenv("MONGODB_DATABASE", DATABASE)
    get_settings.cache_clear()
    await db.get_client().drop_database(DATABASE)
    await ensure_owned_indexes()
    await seed_database(db.get_database(), load_seed_bundle(now=datetime.now(UTC)))
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await db.get_client().drop_database(DATABASE)
    get_settings.cache_clear()


async def _all_pages(
    client: httpx.AsyncClient, limit: int
) -> tuple[list[dict[str, Any]], list[float]]:
    items: list[dict[str, Any]] = []
    durations: list[float] = []
    cursor: str | None = None
    while True:
        params: dict[str, str | int] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        started = time.perf_counter()
        response = await client.get("/api/activities", params=params)
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200, response.text
        page = response.json()
        items.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            return items, durations


async def test_6a_feed_is_newest_first_with_type_mapped_actions_and_gapless_cursor(
    client: httpx.AsyncClient,
) -> None:
    first = (await client.get("/api/activities", params={"limit": 20})).json()
    keys = [(item["detected_at"], item["id"]) for item in first["items"]]
    assert keys == sorted(keys, reverse=True) and len(set(keys)) == len(keys)
    assert first["unseen_count"] > 0

    for item in first["items"]:
        actions = item["actions"]
        assert 1 <= len(actions) <= 2
        assert [action["primary"] for action in actions].count(True) == 1
        if item["activity_type"] in EXECUTION_TYPES:
            assert actions[0]["agent"] == "EXECUTION"
            assert actions[1]["label"] == "Why it matters"
        else:
            assert [action["label"] for action in actions] == ["Plan a response"]
        if item["activity_type"] == "EXECUTIVE_POST":
            assert actions[0]["label"] == "Draft a CEO post"
            assert actions[0]["deliverable_type"] == "CEO_POST"

    items, durations = await _all_pages(client, limit=7)
    ids = [item["id"] for item in items]
    stored = await db.get_database()["competitor_activities"].count_documents(
        {"company_id": get_settings().default_company_id}
    )
    assert len(ids) == len(set(ids)) == stored
    assert sorted(durations)[int(len(durations) * 0.95) - 1] < 1.0


async def test_feed_filters_and_rejects_unknown_enum(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/activities", params={"activity_types": "PRICE_CHANGE"})
    assert {item["activity_type"] for item in response.json()["items"]} == {"PRICE_CHANGE"}

    bogus = await client.get("/api/activities", params={"activity_types": "BOGUS"})
    assert bogus.status_code == 422
    assert bogus.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_mark_seen_lowers_unseen_count(client: httpx.AsyncClient) -> None:
    before = (await client.get("/api/activities")).json()["unseen_count"]
    response = await client.post(
        "/api/activities/mark-seen", json={"up_to": datetime.now(UTC).isoformat()}
    )
    assert response.json() == {"updated": before}
    assert (await client.get("/api/activities")).json()["unseen_count"] == 0


async def test_company_and_tracked_keywords(client: httpx.AsyncClient) -> None:
    company = (await client.get("/api/company")).json()
    assert company["name"] == "Marketing Eye"
    assert len(company["tracked_keywords"]) == 5
    assert company["last_sync_at"] is not None

    saved = await client.put(
        "/api/company/tracked-keywords",
        json={"tracked_keywords": [" AI search ", "ai search", "SEO"]},
    )
    assert saved.json() == {"tracked_keywords": ["AI search", "SEO"]}
    assert (await client.get("/api/company")).json()["tracked_keywords"] == ["AI search", "SEO"]

    for invalid in ([], ["SEO", "  "], [f"k{i}" for i in range(21)]):
        rejected = await client.put(
            "/api/company/tracked-keywords", json={"tracked_keywords": invalid}
        )
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"
    assert (await client.get("/api/company")).json()["tracked_keywords"] == ["AI search", "SEO"]


async def test_seeded_insights_load(client: httpx.AsyncClient) -> None:
    trends = (await client.get("/api/trends")).json()["items"]
    assert trends and [t["momentum_pct"] for t in trends] == sorted(
        (t["momentum_pct"] for t in trends), reverse=True
    )
    assert trends[0]["actions"][0]["label"] == "Get topic ideas"

    influencers = (await client.get("/api/influencers")).json()["items"]
    assert influencers and influencers[0]["actions"][0]["action"] == "DRAFT_OUTREACH"

    assert (await client.get("/api/recommendations")).json() == {"items": []}


async def test_simulate_rejects_real_competitor(client: httpx.AsyncClient) -> None:
    real = await db.get_database()["competitors"].find_one({"is_fictional": False})
    assert real is not None
    response = await client.post("/api/activities/simulate", json={"competitor_id": real["_id"]})
    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "Simulated activity can only be created for fictional demo competitors"
    )


async def test_6b_simulated_signal_arrives_on_the_stream(client: httpx.AsyncClient) -> None:
    company_id = get_settings().default_company_id
    events = feed.stream_activities(
        company_id,
        last_event_id=None,
        is_disconnected=_never,
        poll_seconds=0.5,
        max_seconds=10,
    )
    first_event = asyncio.ensure_future(anext(events))
    await asyncio.sleep(0.2)  # the stream fixes its start point before the signal

    started = time.perf_counter()
    response = await client.post(
        "/api/activities/simulate", json={"activity_type": "EXECUTIVE_POST"}
    )
    assert response.status_code == 201
    created = response.json()
    assert created["is_simulated"] is True and created["is_new"] is True

    event = await asyncio.wait_for(first_event, timeout=3)
    assert time.perf_counter() - started < 3
    assert event["event"] == "activity.created"
    assert event["id"] == created["id"]
    assert json.loads(event["data"])["id"] == created["id"]

    # A reconnect with Last-Event-ID resumes after that item: no duplicate.
    resumed = feed.stream_activities(
        company_id,
        last_event_id=created["id"],
        is_disconnected=_never,
        poll_seconds=0.1,
        max_seconds=0.5,
    )
    assert [item async for item in resumed] == []
    await events.aclose()


async def test_stream_route_speaks_sse(client: httpx.AsyncClient) -> None:
    async with client.stream("GET", "/api/activities/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


async def _never() -> bool:
    return False
