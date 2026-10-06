"""Company, competitor feed and insight routes (api-contract). Validate, then delegate."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Header, Query, Request, status
from sse_starlette import EventSourceResponse

from app.api.deps import SettingsDep
from app.api.schemas.feed import (
    MarkSeenBody,
    SimulateBody,
    TrackedKeywordsBody,
    aware,
    parse_csv,
    parse_ids,
)
from app.intelligence.models import ActivityType, Channel, RecommendationStatus, TrendDirection
from app.orchestration import feed

router = APIRouter(tags=["feed"])

CompanyQuery = Annotated[str | None, Query(alias="company_id", max_length=64)]
# Filters and cursors are short; the bound keeps a huge value out of Mongo queries.
ShortQuery = Annotated[str | None, Query(max_length=1000)]


def _company(settings: SettingsDep, company_id: str | None) -> str:
    return company_id or settings.default_company_id


@router.get("/company")
async def get_company(settings: SettingsDep, company_id: CompanyQuery = None) -> feed.CompanyView:
    return await feed.get_company(_company(settings, company_id))


@router.put("/company/tracked-keywords")
async def put_tracked_keywords(
    body: TrackedKeywordsBody, settings: SettingsDep, company_id: CompanyQuery = None
) -> feed.TrackedKeywords:
    return await feed.set_tracked_keywords(_company(settings, company_id), body.tracked_keywords)


@router.get("/activities")
async def list_activities(
    settings: SettingsDep,
    company_id: CompanyQuery = None,
    activity_types: ShortQuery = None,
    competitor_ids: ShortQuery = None,
    channels: ShortQuery = None,
    since: datetime | None = None,
    cursor: ShortQuery = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> feed.ActivityPage:
    return await feed.list_activities(
        _company(settings, company_id),
        limit=limit,
        cursor=cursor,
        since=aware(since),
        competitor_ids=parse_ids(competitor_ids),
        activity_types=parse_csv(activity_types, ActivityType, "activity_types"),
        channels=parse_csv(channels, Channel, "channels"),
    )


@router.post("/activities/mark-seen")
async def mark_seen(
    body: MarkSeenBody, settings: SettingsDep, company_id: CompanyQuery = None
) -> feed.MarkSeenResult:
    return await feed.mark_seen(_company(settings, company_id), body.up_to)


@router.post("/activities/simulate", status_code=status.HTTP_201_CREATED)
async def simulate(
    body: SimulateBody, settings: SettingsDep, company_id: CompanyQuery = None
) -> feed.ActivityItem:
    return await feed.simulate(
        _company(settings, company_id),
        activity_type=body.activity_type,
        competitor_id=body.competitor_id,
    )


@router.get("/activities/stream")
async def stream(
    request: Request,
    settings: SettingsDep,
    company_id: CompanyQuery = None,
    last_event_id: Annotated[str | None, Header()] = None,
) -> EventSourceResponse:
    events = feed.stream_activities(
        _company(settings, company_id),
        last_event_id=last_event_id,
        is_disconnected=request.is_disconnected,
    )
    return EventSourceResponse(events, ping=15)


@router.get("/trends")
async def list_trends(
    settings: SettingsDep,
    company_id: CompanyQuery = None,
    channels: ShortQuery = None,
    direction: TrendDirection | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> feed.Items[feed.TrendItem]:
    return await feed.list_trends(
        _company(settings, company_id),
        limit=limit,
        channels=parse_csv(channels, Channel, "channels"),
        direction=direction,
    )


@router.get("/influencers")
async def list_influencers(
    settings: SettingsDep,
    company_id: CompanyQuery = None,
    topic: ShortQuery = None,
    channels: ShortQuery = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> feed.Items[feed.InfluencerItem]:
    return await feed.list_influencers(
        _company(settings, company_id),
        limit=limit,
        topic=topic,
        channels=parse_csv(channels, Channel, "channels"),
    )


@router.get("/recommendations")
async def list_recommendations(
    settings: SettingsDep,
    company_id: CompanyQuery = None,
    status: RecommendationStatus = RecommendationStatus.OPEN,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> feed.Items[feed.RecommendationItem]:
    return await feed.list_recommendations(
        _company(settings, company_id), status=status, limit=limit
    )
