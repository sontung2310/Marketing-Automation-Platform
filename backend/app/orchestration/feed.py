"""Read side of the workspace: company, feed and insight views (api-contract).

Every item carries the buttons the UI renders, computed here from specs §6, so
the frontend holds no routing logic.
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from functools import lru_cache
from time import monotonic
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.core.db import get_database
from app.core.errors import NotFoundError, ValidationError
from app.intelligence.models import (
    ICP,
    ActivityAuthor,
    ActivityType,
    AgentName,
    BrandVoice,
    Channel,
    CompetitorActivity,
    DeliverableType,
    Engagement,
    EvidenceLink,
    NextAction,
    Price,
    RecommendationEvidence,
    RecommendationStatus,
    Run,
    SamplePost,
    Service,
    SimulationTemplate,
    Spokesperson,
    TrendDirection,
)
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.trends import TrendsRepository
from app.orchestration.routing import TriggerAction
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.simulation import simulate_activity

T = TypeVar("T")


class ItemAction(BaseModel):
    action: TriggerAction
    label: str
    agent: AgentName
    deliverable_type: DeliverableType | None = None
    primary: bool = False


WHY_IT_MATTERS = ItemAction(
    action=TriggerAction.WHY_IT_MATTERS, label="Why it matters", agent=AgentName.STRATEGY
)
PLAN_A_RESPONSE = [
    ItemAction(
        action=TriggerAction.RESPONSE_PLAN,
        label="Plan a response",
        agent=AgentName.STRATEGY,
        primary=True,
    )
]
USE_TREND = ItemAction(
    action=TriggerAction.USE_TREND, label="Get topic ideas", agent=AgentName.STRATEGY
)
DRAFT_OUTREACH = ItemAction(
    action=TriggerAction.DRAFT_OUTREACH, label="Draft outreach", agent=AgentName.EXECUTION
)
DO_THIS = ItemAction(action=TriggerAction.DO_THIS, label="Do this", agent=AgentName.EXECUTION)

# "Create a similar post" stays on the post's own channel (specs §6).
CHANNEL_POST: dict[Channel, DeliverableType] = {
    Channel.LINKEDIN: DeliverableType.LINKEDIN_POST,
    Channel.X: DeliverableType.X_POST,
    Channel.INSTAGRAM: DeliverableType.INSTAGRAM_POST,
}


def _create_similar(label: str, deliverable: DeliverableType) -> list[ItemAction]:
    primary = ItemAction(
        action=TriggerAction.CREATE_SIMILAR,
        label=label,
        agent=AgentName.EXECUTION,
        deliverable_type=deliverable,
        primary=True,
    )
    return [primary, WHY_IT_MATTERS]


ACTIVITY_ACTIONS: dict[ActivityType, Callable[[Channel], list[ItemAction]]] = {
    ActivityType.NEW_BLOG: lambda _: _create_similar(
        "Create a similar blog", DeliverableType.BLOG_DRAFT
    ),
    ActivityType.SOCIAL_POST: lambda channel: _create_similar(
        "Create a similar post", CHANNEL_POST.get(channel, DeliverableType.LINKEDIN_POST)
    ),
    ActivityType.EXECUTIVE_POST: lambda _: _create_similar(
        "Draft a CEO post", DeliverableType.CEO_POST
    ),
    ActivityType.NEW_PRODUCT: lambda _: PLAN_A_RESPONSE,
    ActivityType.PRODUCT_REMOVED: lambda _: PLAN_A_RESPONSE,
    ActivityType.PRICE_CHANGE: lambda _: PLAN_A_RESPONSE,
    ActivityType.PROMOTION: lambda _: PLAN_A_RESPONSE,
    ActivityType.CAMPAIGN_LAUNCH: lambda _: PLAN_A_RESPONSE,
    ActivityType.PAGE_UPDATE: lambda _: PLAN_A_RESPONSE,
}


# ---------------------------------------------------------------- views


class CompanyView(BaseModel):
    id: str
    name: str
    website: str
    industry: str
    region: str
    summary: str
    icp: list[ICP]
    positioning: str
    services: list[Service]
    brand_voice: BrandVoice
    channels: list[Channel]
    spokesperson: Spokesperson
    tracked_keywords: list[str]
    content_pillars: list[str]
    is_mock: bool
    updated_at: datetime
    last_sync_at: datetime | None


class TrackedKeywords(BaseModel):
    tracked_keywords: list[str]


class ActivityItem(BaseModel):
    id: str
    competitor_id: str
    competitor_name: str
    activity_type: ActivityType
    channel: Channel
    title: str
    summary: str
    url: str | None
    author: ActivityAuthor | None
    price: Price | None
    engagement: Engagement | None
    detected_at: datetime
    is_mock: bool
    is_simulated: bool
    is_new: bool
    actions: list[ItemAction]


class ActivityPage(BaseModel):
    items: list[ActivityItem]
    next_cursor: str | None
    unseen_count: int


class MarkSeenResult(BaseModel):
    updated: int


class TrendItem(BaseModel):
    id: str
    topic: str
    keywords: list[str]
    channel: Channel
    window_days: int
    mention_count: int
    momentum_pct: float
    direction: TrendDirection
    sentiment: float
    sample_posts: list[SamplePost]
    computed_at: datetime
    is_mock: bool
    actions: list[ItemAction]


class InfluencerItem(BaseModel):
    id: str
    name: str
    handle: str
    channel: Channel
    profile_url: str
    followers: int
    engagement_rate: float
    topics: list[str]
    audience_region: str
    relevance_score: float
    evidence: list[EvidenceLink]
    is_mock: bool
    actions: list[ItemAction]


class RecommendationItem(BaseModel):
    id: str
    run_id: str
    session_id: str
    ordinal: int
    kind: str
    title: str
    rationale: str
    priority: str
    channel: Channel | None
    evidence: list[RecommendationEvidence]
    skills_used: list[str]
    next_action: NextAction | None
    status: RecommendationStatus
    created_at: datetime
    run_label: str
    actions: list[ItemAction]


class Items(BaseModel, Generic[T]):
    items: list[T]


# ---------------------------------------------------------------- cursor


def encode_cursor(activity: CompetitorActivity) -> str:
    raw = f"{activity.detected_at.isoformat()}|{activity.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        detected_at, activity_id = base64.urlsafe_b64decode(cursor).decode().split("|", 1)
        return datetime.fromisoformat(detected_at), activity_id
    except ValueError as error:
        raise ValidationError("cursor is invalid") from error


# ---------------------------------------------------------------- services


def activity_item(activity: CompetitorActivity) -> ActivityItem:
    return ActivityItem(
        **activity.model_dump(include=set(ActivityItem.model_fields) - {"is_new", "actions"}),
        is_new=activity.seen_at is None,
        actions=ACTIVITY_ACTIONS[activity.activity_type](activity.channel),
    )


async def get_company(company_id: str) -> CompanyView:
    company = await CompaniesRepository(get_database()).get_for_company(company_id)
    if company is None:
        raise NotFoundError(f"Company {company_id} not found")
    last_sync_at = await CompetitorActivitiesRepository(get_database()).newest_ingested_at(
        company_id
    )
    return CompanyView(**company.model_dump(), last_sync_at=last_sync_at)


async def set_tracked_keywords(company_id: str, keywords: list[str]) -> TrackedKeywords:
    if not await CompaniesRepository(get_database()).set_tracked_keywords(company_id, keywords):
        raise NotFoundError(f"Company {company_id} not found")
    return TrackedKeywords(tracked_keywords=keywords)


async def list_activities(
    company_id: str,
    *,
    limit: int,
    cursor: str | None = None,
    since: datetime | None = None,
    competitor_ids: list[str] | None = None,
    activity_types: list[ActivityType] | None = None,
    channels: list[Channel] | None = None,
) -> ActivityPage:
    repository = CompetitorActivitiesRepository(get_database())
    # One extra record tells whether another page exists.
    activities = await repository.page_for_company(
        company_id,
        limit=limit + 1,
        after=decode_cursor(cursor) if cursor else None,
        since=since,
        competitor_ids=competitor_ids,
        activity_types=activity_types,
        channels=channels,
    )
    page = activities[:limit]
    return ActivityPage(
        items=[activity_item(activity) for activity in page],
        next_cursor=encode_cursor(page[-1]) if len(activities) > limit else None,
        unseen_count=await repository.count_unseen(company_id),
    )


async def mark_seen(company_id: str, up_to: datetime) -> MarkSeenResult:
    updated = await CompetitorActivitiesRepository(get_database()).mark_seen(
        company_id, up_to=up_to, seen_at=datetime.now(UTC)
    )
    return MarkSeenResult(updated=updated)


async def activities_after(company_id: str, after: datetime) -> list[ActivityItem]:
    activities = await CompetitorActivitiesRepository(get_database()).detected_after(
        company_id, after, limit=50
    )
    return [activity_item(activity) for activity in activities]


async def get_activity_detected_at(company_id: str, activity_id: str) -> datetime | None:
    activity = await CompetitorActivitiesRepository(get_database()).get_for_company(
        activity_id, company_id
    )
    return activity.detected_at if activity else None


@lru_cache
def _simulation_templates() -> list[SimulationTemplate]:
    return load_seed_bundle().simulation_templates


async def simulate(
    company_id: str, *, activity_type: ActivityType | None, competitor_id: str | None
) -> ActivityItem:
    activity = await simulate_activity(
        get_database(),
        _simulation_templates(),
        activity_type=activity_type,
        competitor_id=competitor_id,
        company_id=company_id,
    )
    return activity_item(activity)


async def list_trends(
    company_id: str, *, limit: int, channels: list[Channel] | None, direction: TrendDirection | None
) -> Items[TrendItem]:
    trends = await TrendsRepository(get_database()).search_for_company(
        company_id, limit=limit, channels=channels, direction=direction
    )
    return Items[TrendItem](
        items=[
            TrendItem(**trend.model_dump(include=set(TrendItem.model_fields)), actions=[USE_TREND])
            for trend in trends
        ]
    )


async def list_influencers(
    company_id: str, *, limit: int, topic: str | None, channels: list[Channel] | None
) -> Items[InfluencerItem]:
    influencers = await InfluencersRepository(get_database()).search_for_company(
        company_id, limit=limit, topic=topic, channels=channels
    )
    return Items[InfluencerItem](
        items=[
            InfluencerItem(
                **influencer.model_dump(include=set(InfluencerItem.model_fields)),
                actions=[DRAFT_OUTREACH],
            )
            for influencer in influencers
        ]
    )


# Run headers in the Strategy panel name the button that started the run.
TRIGGER_LABELS: dict[str, str] = {
    TriggerAction.CREATE_SIMILAR: "Create similar",
    TriggerAction.WHY_IT_MATTERS: WHY_IT_MATTERS.label,
    TriggerAction.RESPONSE_PLAN: PLAN_A_RESPONSE[0].label,
    TriggerAction.USE_TREND: USE_TREND.label,
    TriggerAction.DRAFT_OUTREACH: DRAFT_OUTREACH.label,
    TriggerAction.DO_THIS: DO_THIS.label,
}


def run_label(run: Run, activity_types: dict[str, ActivityType]) -> str:
    """`<button label> · <triggering item type>` (api-contract `run_label`)."""
    action = str(run.trigger.get("action", ""))
    ref_id = str(run.trigger.get("ref_id", ""))
    if action not in TRIGGER_LABELS:
        return run.intent
    item_type = activity_types.get(ref_id) or str(run.trigger.get("kind", ""))
    return f"{TRIGGER_LABELS[action]} · {item_type}" if item_type else TRIGGER_LABELS[action]


async def list_recommendations(
    company_id: str, *, status: RecommendationStatus, limit: int
) -> Items[RecommendationItem]:
    rows = await RecommendationsRepository(get_database()).list_for_company(
        company_id, status=status, limit=limit
    )
    ref_ids = {str(run.trigger.get("ref_id")) for _, run in rows if run.trigger.get("ref_id")}
    activities = await CompetitorActivitiesRepository(get_database()).get_many_for_company(
        sorted(ref_ids), company_id
    )
    activity_types = {activity.id: activity.activity_type for activity in activities}
    return Items[RecommendationItem](
        items=[
            RecommendationItem(
                **recommendation.model_dump(include=set(RecommendationItem.model_fields)),
                created_at=run.started_at,
                run_label=run_label(run, activity_types),
                actions=[DO_THIS],
            )
            for recommendation, run in rows
        ]
    )


STREAM_POLL_SECONDS = 3.0
# ponytail: serverless caps a function's duration, so the stream ends itself and
# EventSource reconnects with Last-Event-ID. Use a change stream on a long-lived host.
STREAM_MAX_SECONDS = 55.0


async def stream_activities(
    company_id: str,
    *,
    last_event_id: str | None,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_seconds: float = STREAM_POLL_SECONDS,
    max_seconds: float = STREAM_MAX_SECONDS,
) -> AsyncGenerator[dict[str, str]]:
    """`activity.created` events for activities detected after the stream opened,
    or after the `Last-Event-ID` item when a client reconnects."""
    resumed = await get_activity_detected_at(company_id, last_event_id) if last_event_id else None
    after = resumed or datetime.now(UTC)
    deadline = monotonic() + max_seconds
    while monotonic() < deadline and not await is_disconnected():
        for item in await activities_after(company_id, after):
            after = item.detected_at
            yield {"event": "activity.created", "id": item.id, "data": item.model_dump_json()}
        await asyncio.sleep(poll_seconds)
