"""Step 6 read side against a real, seeded MongoDB (roadmap 6-A, 6-B)."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

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

EXECUTION_TYPES = {"NEW_BLOG", "SOCIAL_POST", "EXECUTIVE_POST"}


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[httpx.AsyncClient]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    # A unique name per test: parallel runs never share or race a dropping database.
    database = f"ma_api_test_{uuid4().hex[:12]}"  # Atlas caps names at 38 bytes
    monkeypatch.setenv("MONGODB_DATABASE", database)
    get_settings.cache_clear()
    await ensure_owned_indexes()
    await seed_database(db.get_database(), load_seed_bundle(now=datetime.now(UTC)))
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await db.get_client().drop_database(database)
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
    scores = [i["relevance_score"] for i in influencers]
    assert scores == sorted(scores, reverse=True)

    assert (await client.get("/api/recommendations")).json() == {"items": []}


async def test_researched_trend_is_served_and_counts_as_a_sync(client: httpx.AsyncClient) -> None:
    computed_at = datetime.now(UTC) + timedelta(minutes=5)  # newer than any seeded record
    await db.get_database()["trends"].insert_one(
        {
            "_id": "trd_l30d_test",
            "company_id": get_settings().default_company_id,
            "topic": "Social Media Marketing",
            "keywords": [],
            "channel": "TIKTOK",
            "window_days": 30,
            "mention_count": 3,
            "momentum_pct": 9999.0,
            "direction": "RISING",
            "sentiment": 0.2,
            "sample_posts": [{"title": "Post", "url": "https://tiktok.com/x", "channel": "TIKTOK"}],
            "summary": "Tactics versus tooling frustration.",
            "computed_at": computed_at,
            "source": {"system": "LAST30DAYS", "ref_id": "trend:test"},
            "is_mock": False,
        }
    )
    top = (await client.get("/api/trends", params={"limit": 1})).json()["items"][0]
    assert (top["id"], top["channel"], top["summary"]) == (
        "trd_l30d_test",
        "TIKTOK",
        "Tactics versus tooling frustration.",
    )
    company = (await client.get("/api/company")).json()
    assert datetime.fromisoformat(company["last_sync_at"]) == computed_at.replace(
        microsecond=computed_at.microsecond // 1000 * 1000
    )


async def test_recommendations_are_newest_run_first(client: httpx.AsyncClient) -> None:
    database = db.get_database()
    company_id = get_settings().default_company_id
    now = datetime.now(UTC)
    session = {"_id": "ses_t", "company_id": company_id, "created_at": now}
    await database["sessions"].insert_one(session)
    for run_id, started_at in (("run_old", now - timedelta(hours=1)), ("run_new", now)):
        await database["runs"].insert_one(
            {
                "_id": run_id,
                "session_id": "ses_t",
                "agent": "STRATEGY",
                "intent": "TOPIC_RECOMMENDATION",
                "trigger": {},
                "status": "SUCCEEDED",
                "started_at": started_at,
            }
        )
        for ordinal in (1, 2):
            await database["recommendations"].insert_one(
                {
                    "_id": f"rec_{run_id}_{ordinal}",
                    "run_id": run_id,
                    "session_id": "ses_t",
                    "ordinal": ordinal,
                    "kind": "CONTENT_TOPIC",
                    "title": "Topic",
                    "rationale": "Why",
                    "priority": "HIGH",
                    "evidence": [{"id": "trd_x", "kind": "trend", "note": "Rising"}],
                    "status": "OPEN",
                }
            )
    items = (await client.get("/api/recommendations")).json()["items"]
    assert [(i["run_id"], i["ordinal"]) for i in items] == [
        ("run_new", 1),
        ("run_new", 2),
        ("run_old", 1),
        ("run_old", 2),
    ]
    assert items[0]["actions"][0]["label"] == "Do this"


async def test_simulate_rejects_real_competitor(client: httpx.AsyncClient) -> None:
    real = await db.get_database()["competitors"].find_one({"is_fictional": False})
    assert real is not None
    activities = db.get_database()["competitor_activities"]
    before = await activities.count_documents({})
    response = await client.post("/api/activities/simulate", json={"competitor_id": real["_id"]})
    assert response.status_code == 422
    assert await activities.count_documents({}) == before
    assert response.json()["error"]["message"] == (
        "Simulated activity can only be created for fictional demo competitors"
    )


def _stream(last_event_id: str | None, *, max_seconds: float) -> AsyncGenerator[dict[str, Any]]:
    return feed.stream_activities(
        get_settings().default_company_id,
        last_event_id=last_event_id,
        is_disconnected=_never,
        poll_seconds=0.1,
        max_seconds=max_seconds,
    )


async def test_6b_simulated_signal_arrives_on_the_stream(client: httpx.AsyncClient) -> None:
    events = _stream(None, max_seconds=10)
    opening = await anext(events)
    assert opening["id"] and "data" not in opening  # the position a reconnect resumes from
    first_event = asyncio.ensure_future(anext(events))

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
    assert json.loads(event["data"])["id"] == created["id"]
    await events.aclose()

    # A reconnect with that Last-Event-ID resumes after the item: no duplicate.
    resumed = [item async for item in _stream(str(event["id"]), max_seconds=0.3)]
    assert [item for item in resumed if "data" in item] == []


async def test_quiet_stream_reconnect_still_delivers_the_gap(client: httpx.AsyncClient) -> None:
    """Review finding: a window with no events must still leave a resumable position."""
    quiet = _stream(None, max_seconds=0.3)
    opening = await anext(quiet)
    assert [item async for item in quiet] == []  # the window closes with nothing sent

    created = (
        await client.post("/api/activities/simulate", json={"activity_type": "PRICE_CHANGE"})
    ).json()

    resumed = [item async for item in _stream(str(opening["id"]), max_seconds=0.3)]
    delivered = [json.loads(item["data"])["id"] for item in resumed if "data" in item]
    assert delivered == [created["id"]]


async def test_unknown_last_event_id_starts_from_now(client: httpx.AsyncClient) -> None:
    events = [item async for item in _stream("act_not_a_position", max_seconds=0.2)]
    assert [item for item in events if "data" in item] == []


async def test_stream_route_speaks_sse(client: httpx.AsyncClient) -> None:
    async with client.stream("GET", "/api/activities/stream") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


async def _never() -> bool:
    return False


async def test_unexpected_errors_use_the_envelope(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_: object, **__: object) -> None:
        raise RuntimeError("secret detail")

    monkeypatch.setattr(feed, "list_trends", boom)
    transport = httpx.ASGITransport(app=create_app(), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await http.get("/api/trends")
    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "INTERNAL",
        "message": "Unexpected server error",
        "details": {},
    }
