"""Real-HTTP integration coverage for the Marketing Intelligence MCP service."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from agents import Agent, RunContextWrapper
from agents.mcp import MCPServerStreamableHttp
from mcp.types import CallToolResult, TextContent
from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.models import (
    ICP,
    ActivityType,
    BrandVoice,
    Channel,
    Company,
    Competitor,
    CompetitorActivity,
    Influencer,
    Price,
    Priority,
    Provenance,
    Recommendation,
    RecommendationStatus,
    Service,
    Session,
    SourceSystem,
    Trend,
    TrendDirection,
)
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.indexes import ensure_indexes
from app.intelligence.repositories.sessions import SessionsRepository
from app.mcp_server.contracts import NO_RECORDS_MATCHED_NOTE
from app.mcp_server.server import McpRepositories
from evals.runtime import serve_mcp

pytestmark = pytest.mark.integration

COMPANY_ID = "cmp_marketing_eye"
OTHER_COMPANY_ID = "cmp_other_company"
PRIMARY_COMPETITOR_ID = "cpt_brightlane"
OTHER_COMPETITOR_ID = "cpt_other_company"
PRIMARY_INFLUENCER_ID = "inf_tech_voices"
PRIMARY_RECOMMENDATION_ID = "rec_price_response"
OTHER_RECOMMENDATION_ID = "rec_other_company"
_COMPACT_ACTIVITY_KEYS = {
    "id",
    "competitor_name",
    "activity_type",
    "channel",
    "title",
    "summary",
    "url",
    "price",
    "detected_at",
    "is_mock",
    "is_simulated",
}
_COMPACT_COMPETITOR_KEYS = {"id", "name", "website", "is_fictional", "channels"}


@dataclass(frozen=True)
class McpService:
    database: AsyncDatabase[Document]
    endpoint: str
    now: datetime


@pytest.fixture
async def mcp_service() -> AsyncIterator[McpService]:
    """Serve test-only, time-relative records from an isolated Mongo database."""

    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")

    database_name = f"ma_mcp_{uuid4().hex[:16]}"
    database = db.get_client()[database_name]
    now = datetime.now(UTC)
    try:
        await db.get_client().drop_database(database_name)
        await ensure_indexes(database)
        await _load_records(McpRepositories.for_database(database), now)
        async with serve_mcp(database, COMPANY_ID, now=lambda: now) as endpoint:
            yield McpService(database=database, endpoint=endpoint, now=now)
    finally:
        await db.get_client().drop_database(database_name)


async def test_real_http_client_lists_the_nine_described_tools(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        agent = Agent[None](name="MCP discovery", mcp_servers=[client])
        tools = await agent.get_mcp_tools(RunContextWrapper(context=None))

    assert [tool.name for tool in tools] == [
        "get_company_context",
        "list_competitors",
        "search_competitor_activity",
        "get_competitor_activity",
        "summarize_competitor_activity",
        "search_trends",
        "search_influencers",
        "get_influencer",
        "get_recommendation",
    ]
    assert all(tool.description for tool in tools)


async def test_raw_enum_values_are_advertised_on_array_items(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    activity_items = tools["search_competitor_activity"].input_schema["properties"][
        "activity_types"
    ]["anyOf"][0]["items"]
    channel_items = tools["search_influencers"].input_schema["properties"]["channels"]["anyOf"][0][
        "items"
    ]
    direction = tools["search_trends"].input_schema["properties"]["direction"]["anyOf"][0]
    assert activity_items["enum"] == [item.value for item in ActivityType]
    assert channel_items["enum"] == [item.value for item in Channel]
    assert direction["enum"] == [item.value for item in TrendDirection]


async def test_transport_security_allows_loopback_and_compose_service_hosts(
    mcp_service: McpService,
) -> None:
    async with _client(mcp_service) as loopback_client:
        loopback_tools = await loopback_client.list_tools()
    async with _client(mcp_service, headers={"Host": "mcp:8001"}) as compose_client:
        compose_tools = await compose_client.list_tools()

    assert len(loopback_tools) == 9
    assert len(compose_tools) == 9


async def test_activity_search_is_tenant_scoped_filtered_and_newest_first(
    mcp_service: McpService,
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool(
            "search_competitor_activity",
            {
                "activity_types": [ActivityType.PRICE_CHANGE.value],
                "since_days": 30,
                "limit": 25,
            },
        )

    payload = _tool_json(result)
    activities = payload["results"]
    assert isinstance(activities, list)
    assert activities
    assert [activity["id"] for activity in activities] == [
        f"act_price_{index:03d}" for index in range(1, 25)
    ]
    assert all(activity["id"].startswith("act_") for activity in activities)
    assert all(set(activity) == _COMPACT_ACTIVITY_KEYS for activity in activities)
    assert all(
        activity["activity_type"] == ActivityType.PRICE_CHANGE.value for activity in activities
    )
    assert all(activity["competitor_name"] == "Brightlane" for activity in activities)
    assert [activity["detected_at"] for activity in activities] == sorted(
        (activity["detected_at"] for activity in activities), reverse=True
    )


async def test_company_context_is_tenant_specific(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        context = _tool_json(await client.call_tool("get_company_context", {}))

    assert context["id"] == COMPANY_ID
    assert context["name"] == "Marketing Eye"
    assert context["id"] != OTHER_COMPANY_ID


async def test_cross_tenant_activity_get_returns_not_found(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("get_competitor_activity", {"activity_id": "act_price_099"})

    assert _tool_json(result)["error"]["code"] == "NOT_FOUND"


async def test_cross_tenant_influencer_get_returns_not_found(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("get_influencer", {"influencer_id": "inf_other_company"})

    assert _tool_json(result)["error"]["code"] == "NOT_FOUND"


async def test_list_and_search_tools_exclude_other_company_records(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        competitors = _tool_json(await client.call_tool("list_competitors", {}))
        activities = _tool_json(await client.call_tool("search_competitor_activity", {"limit": 25}))
        trends = _tool_json(await client.call_tool("search_trends", {}))
        influencers = _tool_json(await client.call_tool("search_influencers", {}))

    assert [item["id"] for item in competitors["results"]] == [PRIMARY_COMPETITOR_ID]
    assert all(set(item) == _COMPACT_COMPETITOR_KEYS for item in competitors["results"])
    assert competitors["results"][0]["channels"] == [Channel.LINKEDIN.value]
    assert all(activity["id"] != "act_price_099" for activity in activities["results"])
    assert [item["id"] for item in trends["results"]] == ["trd_ai_marketing"]
    assert [item["id"] for item in influencers["results"]] == [PRIMARY_INFLUENCER_ID]


async def test_recommendation_lookup_derives_tenancy_from_its_session(
    mcp_service: McpService,
) -> None:
    async with _client(mcp_service) as client:
        own_result = await client.call_tool(
            "get_recommendation", {"recommendation_id": PRIMARY_RECOMMENDATION_ID}
        )
        other_result = await client.call_tool(
            "get_recommendation", {"recommendation_id": OTHER_RECOMMENDATION_ID}
        )

    assert _tool_json(own_result)["id"] == PRIMARY_RECOMMENDATION_ID
    assert _tool_json(other_result)["error"]["code"] == "NOT_FOUND"


async def test_invalid_enum_uses_a_non_error_validation_envelope(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", {"activity_types": ["BOGUS"]})

    assert result.is_error is False
    assert _tool_json(result)["error"]["code"] == "VALIDATION_ERROR"


async def test_unknown_activity_id_uses_a_non_error_not_found_envelope(
    mcp_service: McpService,
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("get_competitor_activity", {"activity_id": "act_missing"})

    assert result.is_error is False
    assert _tool_json(result)["error"]["code"] == "NOT_FOUND"


async def test_empty_search_returns_an_explanatory_note_without_fallback(
    mcp_service: McpService,
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", {"query": "quantum knitting"})

    assert _tool_json(result) == {"results": [], "note": NO_RECORDS_MATCHED_NOTE}


async def test_limited_search_defaults_to_ten_results(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", {})

    assert len(_tool_json(result)["results"]) == 10


async def test_limited_search_caps_results_at_twenty_five(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", {"limit": 500})

    assert len(_tool_json(result)["results"]) == 25


@pytest.mark.parametrize("arguments", [{"limit": 0}, {"since_days": 0}])
async def test_invalid_activity_search_lower_bound_uses_validation_envelope(
    mcp_service: McpService,
    arguments: dict[str, int],
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", arguments)

    assert result.is_error is False
    assert _tool_json(result)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("search_competitor_activity", {"since_days": 366}),
        ("summarize_competitor_activity", {"since_days": 366}),
    ],
)
async def test_since_days_upper_bound_uses_validation_envelope(
    mcp_service: McpService,
    tool_name: str,
    arguments: dict[str, int],
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is False
    assert _tool_json(result)["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        ("search_competitor_activity", {"query": "x" * 201}),
        ("search_competitor_activity", {"competitor_ids": ["cpt_brightlane"] * 26}),
        ("search_trends", {"query": "x" * 201}),
        ("search_influencers", {"topic": "x" * 201}),
        ("search_influencers", {"region": "x" * 201}),
    ],
)
async def test_text_and_list_bounds_use_validation_envelopes(
    mcp_service: McpService,
    tool_name: str,
    arguments: dict[str, object],
) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is False
    assert _tool_json(result)["error"]["code"] == "VALIDATION_ERROR"


async def test_trend_text_search_hits_indexed_records(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_trends", {"query": "AI"})

    assert [item["id"] for item in _tool_json(result)["results"]] == ["trd_ai_marketing"]


async def test_influencer_text_search_hits_indexed_records(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_influencers", {"topic": "AI"})

    assert [item["id"] for item in _tool_json(result)["results"]] == [PRIMARY_INFLUENCER_ID]


async def test_empty_activity_summary_remains_a_noted_summary(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("summarize_competitor_activity", {"since_days": 1})

    assert _tool_json(result) == {
        "counts": [],
        "recent_items": [],
        "note": NO_RECORDS_MATCHED_NOTE,
    }


async def test_activity_summary_embeds_compact_recent_items(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("summarize_competitor_activity", {})

    payload = _tool_json(result)
    assert "note" not in payload
    recent_items = payload["recent_items"]
    assert isinstance(recent_items, list)
    assert recent_items
    first_recent = recent_items[0]
    assert isinstance(first_recent, dict)
    items = first_recent["items"]
    assert isinstance(items, list)
    assert items
    assert all(isinstance(item, dict) and set(item) == _COMPACT_ACTIVITY_KEYS for item in items)


async def test_json_type_mismatch_is_rejected_by_the_mcp_sdk(mcp_service: McpService) -> None:
    async with _client(mcp_service) as client:
        result = await client.call_tool("search_competitor_activity", {"since_days": "abc"})

    assert result.is_error is True
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert "since_days" in result.content[0].text


async def test_all_tools_leave_owned_collections_unchanged(mcp_service: McpService) -> None:
    before = await _collection_snapshot(mcp_service.database)

    async with _client(mcp_service) as client:
        calls = (
            ("get_company_context", {}),
            ("list_competitors", {}),
            ("search_competitor_activity", {"activity_types": ["PRICE_CHANGE"]}),
            ("get_competitor_activity", {"activity_id": "act_price_001"}),
            ("summarize_competitor_activity", {}),
            ("search_trends", {}),
            ("search_influencers", {}),
            ("get_influencer", {"influencer_id": PRIMARY_INFLUENCER_ID}),
            ("get_recommendation", {"recommendation_id": PRIMARY_RECOMMENDATION_ID}),
        )
        for tool_name, arguments in calls:
            assert (await client.call_tool(tool_name, arguments)).is_error is False

    assert await _collection_snapshot(mcp_service.database) == before


def _client(
    mcp_service: McpService, *, headers: dict[str, str] | None = None
) -> MCPServerStreamableHttp:
    params: dict[str, object] = {"url": mcp_service.endpoint}
    if headers is not None:
        params["headers"] = headers
    return MCPServerStreamableHttp(params, use_structured_content=False)


def _tool_json(result: CallToolResult) -> dict[str, object]:
    assert result.is_error is False
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    text = result.content[0].text
    payload = json.loads(text)
    assert isinstance(payload, dict)
    return payload


async def _load_records(repositories: McpRepositories, now: datetime) -> None:
    companies = repositories.companies
    competitors = repositories.competitors
    activities = repositories.activities
    trends = repositories.trends
    influencers = repositories.influencers
    sessions = SessionsRepository(companies.database)
    recommendations = repositories.recommendations

    await companies.upsert(_company(COMPANY_ID, "Marketing Eye", now))
    await companies.upsert(_company(OTHER_COMPANY_ID, "Other Company", now))
    await competitors.upsert(_competitor(COMPANY_ID, PRIMARY_COMPETITOR_ID, "Brightlane"))
    await competitors.upsert(_competitor(OTHER_COMPANY_ID, OTHER_COMPETITOR_ID, "Other Competitor"))
    for index in range(1, 25):
        await activities.upsert(_price_activity(index, now))
    await activities.upsert(_social_activity("act_social_recent", now))
    await activities.upsert(_price_activity(90, now, detected_at=now - timedelta(days=90)))
    await activities.upsert(
        _price_activity(
            99,
            now,
            company_id=OTHER_COMPANY_ID,
            competitor_id=OTHER_COMPETITOR_ID,
            detected_at=now - timedelta(hours=1),
        )
    )
    await trends.upsert(_trend(COMPANY_ID, "trd_ai_marketing", now))
    await trends.upsert(_trend(OTHER_COMPANY_ID, "trd_other_company", now))
    await influencers.upsert(_influencer(COMPANY_ID, PRIMARY_INFLUENCER_ID))
    await influencers.upsert(_influencer(OTHER_COMPANY_ID, "inf_other_company"))
    await sessions.upsert(_session("ses_marketing_eye", COMPANY_ID, now))
    await sessions.upsert(_session("ses_other_company", OTHER_COMPANY_ID, now))
    await recommendations.upsert(
        _recommendation(PRIMARY_RECOMMENDATION_ID, "ses_marketing_eye", "run_mcp_test")
    )
    await recommendations.upsert(
        _recommendation(OTHER_RECOMMENDATION_ID, "ses_other_company", "run_other_test")
    )


def _company(company_id: str, name: str, now: datetime) -> Company:
    return Company(
        _id=company_id,
        name=name,
        website=f"https://{company_id}.example",
        industry="Marketing",
        region="AU",
        summary="A test company.",
        icp=[ICP(segment="B2B", pains=["Noise"], goals=["Growth"])],
        positioning="Clear positioning.",
        services=[Service(name="Strategy", description="Marketing strategy.", price_from=1)],
        brand_voice=BrandVoice(tone=["clear"], do=["help"], dont=["hype"], sample_copy=["Useful."]),
        channels=[Channel.LINKEDIN],
        content_pillars=["Growth"],
        is_mock=True,
        updated_at=now,
    )


def _competitor(company_id: str, competitor_id: str, name: str) -> Competitor:
    return Competitor(
        _id=competitor_id,
        company_id=company_id,
        name=name,
        website=f"https://{competitor_id}.example",
        is_fictional=True,
        social={Channel.LINKEDIN: f"https://linkedin.example/{competitor_id}", Channel.X: None},
        source=_source(competitor_id),
        is_mock=True,
    )


def _price_activity(
    index: int,
    now: datetime,
    *,
    company_id: str = COMPANY_ID,
    competitor_id: str = PRIMARY_COMPETITOR_ID,
    detected_at: datetime | None = None,
) -> CompetitorActivity:
    detected_at = detected_at or now - timedelta(days=2, hours=index)
    return CompetitorActivity(
        _id=f"act_price_{index:03d}",
        company_id=company_id,
        competitor_id=competitor_id,
        competitor_name="Brightlane" if company_id == COMPANY_ID else "Other Competitor",
        activity_type=ActivityType.PRICE_CHANGE,
        channel=Channel.WEBSITE,
        title=f"Price change {index}",
        summary="A monitored price change.",
        price=Price(before=100, after=90, currency="AUD"),
        occurred_at=detected_at - timedelta(hours=1),
        detected_at=detected_at,
        source=_source(f"activity-{company_id}-{index}"),
        is_mock=True,
        is_simulated=False,
        ingested_at=now,
    )


def _social_activity(activity_id: str, now: datetime) -> CompetitorActivity:
    detected_at = now - timedelta(hours=25)
    return CompetitorActivity(
        _id=activity_id,
        company_id=COMPANY_ID,
        competitor_id=PRIMARY_COMPETITOR_ID,
        competitor_name="Brightlane",
        activity_type=ActivityType.SOCIAL_POST,
        channel=Channel.LINKEDIN,
        title="Recent social post",
        summary="A recent non-price activity.",
        url="https://brightlane.example/social-recent",
        occurred_at=detected_at - timedelta(hours=1),
        detected_at=detected_at,
        source=_source(f"activity-{activity_id}"),
        is_mock=True,
        is_simulated=False,
        ingested_at=now,
    )


def _trend(company_id: str, trend_id: str, now: datetime) -> Trend:
    return Trend(
        _id=trend_id,
        company_id=company_id,
        topic="AI marketing",
        keywords=["AI"],
        channel=Channel.LINKEDIN,
        window_days=7,
        mention_count=10,
        momentum_pct=12.5,
        direction=TrendDirection.RISING,
        sentiment=0.5,
        sample_posts=[
            {"title": "AI marketing", "url": "https://trend.example/post", "channel": "LINKEDIN"}
        ],
        computed_at=now,
        source=_source(trend_id),
        is_mock=True,
    )


def _influencer(company_id: str, influencer_id: str) -> Influencer:
    return Influencer(
        _id=influencer_id,
        company_id=company_id,
        name="Tech Voices",
        handle="@techvoices",
        channel=Channel.LINKEDIN,
        profile_url="https://influencer.example/techvoices",
        followers=50_000,
        engagement_rate=0.1,
        topics=["AI"],
        audience_region="AU",
        relevance_score=0.9,
        evidence=[],
        source=_source(influencer_id),
        is_mock=True,
    )


def _session(session_id: str, company_id: str, now: datetime) -> Session:
    return Session(_id=session_id, company_id=company_id, created_at=now)


def _recommendation(recommendation_id: str, session_id: str, run_id: str) -> Recommendation:
    return Recommendation(
        _id=recommendation_id,
        run_id=run_id,
        session_id=session_id,
        ordinal=1,
        kind="COMPETITIVE_RESPONSE",
        title="Respond to price change",
        rationale="A test recommendation.",
        priority=Priority.HIGH,
        evidence=[{"id": "act_price_001", "kind": "activity", "note": "Recent price change."}],
        status=RecommendationStatus.OPEN,
    )


def _source(ref_id: str) -> Provenance:
    return Provenance(system=SourceSystem.MOCK_SEED, ref_id=ref_id)


async def _collection_snapshot(database: AsyncDatabase[Document]) -> dict[str, list[Document]]:
    collections = (
        "companies",
        "competitors",
        "competitor_activities",
        "trends",
        "influencers",
        "sessions",
        "recommendations",
    )
    return {
        collection: [
            document async for document in database[collection].find({}).sort("_id", ASCENDING)
        ]
        for collection in collections
    }
