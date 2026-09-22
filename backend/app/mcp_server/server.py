"""Read-only Marketing Intelligence MCP server and application factory."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Annotated, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.applications import Starlette

from app.intelligence.models import ActivityType, Channel, ModelBase, TrendDirection
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.trends import TrendsRepository
from app.mcp_server.contracts import (
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_TOOL_LIMIT,
    NO_RECORDS_MATCHED_NOTE,
    ActivityIdArguments,
    ActivityResult,
    ActivityResults,
    ActivitySearchArguments,
    ActivitySummaryArguments,
    ActivitySummaryResult,
    CompanyResult,
    CompetitorResults,
    InfluencerIdArguments,
    InfluencerResult,
    InfluencerResults,
    InfluencerSearchArguments,
    RecommendationIdArguments,
    RecommendationResult,
    ResultsResponse,
    ToolErrorEnvelope,
    TrendResults,
    TrendSearchArguments,
    capped_limit,
    compact_activity,
    compact_activity_summary,
    compact_competitor,
    not_found,
    parse_tool_arguments,
    record_response,
)

ActivityTypeValue = Annotated[
    str,
    Field(json_schema_extra={"enum": [activity_type.value for activity_type in ActivityType]}),
]
ChannelValue = Annotated[
    str,
    Field(json_schema_extra={"enum": [channel.value for channel in Channel]}),
]
TrendDirectionValue = Annotated[
    str,
    Field(json_schema_extra={"enum": [direction.value for direction in TrendDirection]}),
]
ResponseItemT = TypeVar("ResponseItemT", bound=ModelBase)


class McpRepositories:
    """The only repository operations exposed to MCP tool handlers."""

    def __init__(
        self,
        *,
        companies: CompaniesRepository,
        competitors: CompetitorsRepository,
        activities: CompetitorActivitiesRepository,
        trends: TrendsRepository,
        influencers: InfluencersRepository,
        recommendations: RecommendationsRepository,
    ) -> None:
        self.companies = companies
        self.competitors = competitors
        self.activities = activities
        self.trends = trends
        self.influencers = influencers
        self.recommendations = recommendations


def build_mcp_server(
    repositories: McpRepositories,
    *,
    company_id: str,
    now: Callable[[], datetime] | None = None,
) -> MCPServer[object]:
    """Create a configured server whose handlers only delegate repository reads."""

    current_time = now or _utc_now
    server: MCPServer[object] = MCPServer(
        "marketing-intelligence",
        description="Tenant-scoped, read-only marketing intelligence evidence.",
        version="0.1.0",
    )

    @server.tool(
        description="Return the configured company's marketing context.", structured_output=False
    )
    async def get_company_context() -> CompanyResult:
        company = await repositories.companies.get_for_company(company_id)
        if company is None:
            return not_found("The configured company context was not found.")
        return record_response(company)

    @server.tool(
        description="List competitors owned by the configured company.", structured_output=False
    )
    async def list_competitors() -> CompetitorResults:
        competitors = await repositories.competitors.list_for_company(company_id)
        return _results_or_note([compact_competitor(competitor) for competitor in competitors])

    @server.tool(
        description="Search recent competitor activity with optional raw JSON filters.",
        structured_output=False,
    )
    async def search_competitor_activity(
        query: str | None = None,
        competitor_ids: list[str] | None = None,
        activity_types: list[ActivityTypeValue] | None = None,
        channels: list[ChannelValue] | None = None,
        since_days: int | None = DEFAULT_LOOKBACK_DAYS,
        limit: int | None = DEFAULT_TOOL_LIMIT,
    ) -> ActivityResults:
        parsed = parse_tool_arguments(
            ActivitySearchArguments,
            {
                "query": query,
                "competitor_ids": competitor_ids,
                "activity_types": activity_types,
                "channels": channels,
                "since_days": since_days,
                "limit": limit,
            },
        )
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        activities = await repositories.activities.search_for_company(
            company_id,
            detected_since=current_time() - timedelta(days=parsed.since_days),
            limit=capped_limit(parsed.limit),
            query=parsed.query,
            competitor_ids=parsed.competitor_ids,
            activity_types=parsed.activity_types,
            channels=parsed.channels,
        )
        return _results_or_note([compact_activity(activity) for activity in activities])

    @server.tool(
        description="Return one configured-company competitor activity by its act_ ID.",
        structured_output=False,
    )
    async def get_competitor_activity(activity_id: str) -> ActivityResult:
        parsed = parse_tool_arguments(ActivityIdArguments, {"activity_id": activity_id})
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        activity = await repositories.activities.get_for_company(parsed.activity_id, company_id)
        if activity is None:
            return not_found("No competitor activity matched that ID.")
        return record_response(activity)

    @server.tool(
        description=(
            "Summarize recent configured-company competitor activity by type and competitor."
        ),
        structured_output=False,
    )
    async def summarize_competitor_activity(
        since_days: int | None = DEFAULT_LOOKBACK_DAYS,
    ) -> ActivitySummaryResult:
        parsed = parse_tool_arguments(ActivitySummaryArguments, {"since_days": since_days})
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        summary = await repositories.activities.summarize_for_company(
            company_id,
            detected_since=current_time() - timedelta(days=parsed.since_days),
        )
        if not summary.counts and not summary.recent_items:
            summary = summary.model_copy(update={"note": NO_RECORDS_MATCHED_NOTE})
        return record_response(compact_activity_summary(summary))

    @server.tool(
        description="Search configured-company trends with optional raw JSON filters.",
        structured_output=False,
    )
    async def search_trends(
        query: str | None = None,
        channels: list[ChannelValue] | None = None,
        direction: TrendDirectionValue | None = None,
        limit: int | None = DEFAULT_TOOL_LIMIT,
    ) -> TrendResults:
        parsed = parse_tool_arguments(
            TrendSearchArguments,
            {"query": query, "channels": channels, "direction": direction, "limit": limit},
        )
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        trends = await repositories.trends.search_for_company(
            company_id,
            limit=capped_limit(parsed.limit),
            query=parsed.query,
            channels=parsed.channels,
            direction=parsed.direction,
        )
        return _results_or_note(trends)

    @server.tool(
        description="Search configured-company influencers with optional raw JSON filters.",
        structured_output=False,
    )
    async def search_influencers(
        topic: str | None = None,
        channels: list[ChannelValue] | None = None,
        region: str | None = None,
        min_followers: int | None = None,
        limit: int | None = DEFAULT_TOOL_LIMIT,
    ) -> InfluencerResults:
        parsed = parse_tool_arguments(
            InfluencerSearchArguments,
            {
                "topic": topic,
                "channels": channels,
                "region": region,
                "min_followers": min_followers,
                "limit": limit,
            },
        )
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        influencers = await repositories.influencers.search_for_company(
            company_id,
            limit=capped_limit(parsed.limit),
            topic=parsed.topic,
            channels=parsed.channels,
            region=parsed.region,
            min_followers=parsed.min_followers,
        )
        return _results_or_note(influencers)

    @server.tool(
        description="Return one configured-company influencer by its inf_ ID.",
        structured_output=False,
    )
    async def get_influencer(influencer_id: str) -> InfluencerResult:
        parsed = parse_tool_arguments(InfluencerIdArguments, {"influencer_id": influencer_id})
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        influencer = await repositories.influencers.get_for_company(
            parsed.influencer_id, company_id
        )
        if influencer is None:
            return not_found("No influencer matched that ID.")
        return record_response(influencer)

    @server.tool(
        description="Return one recommendation when its session belongs to the configured company.",
        structured_output=False,
    )
    async def get_recommendation(recommendation_id: str) -> RecommendationResult:
        parsed = parse_tool_arguments(
            RecommendationIdArguments, {"recommendation_id": recommendation_id}
        )
        if isinstance(parsed, ToolErrorEnvelope):
            return parsed
        recommendation = await repositories.recommendations.get_for_company(
            parsed.recommendation_id, company_id
        )
        if recommendation is None:
            return not_found("No recommendation matched that ID for the configured company.")
        return record_response(recommendation)

    return server


def build_mcp_app(
    repositories: McpRepositories,
    *,
    company_id: str,
    now: Callable[[], datetime] | None = None,
    host: str = "127.0.0.1",
    allowed_hosts: Sequence[str] | None = None,
) -> Starlette:
    """Build the streamable-HTTP ASGI application without a database dependency."""

    server = build_mcp_server(repositories, company_id=company_id, now=now)
    security = None
    if allowed_hosts is not None:
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(allowed_hosts),
        )
    return server.streamable_http_app(
        streamable_http_path="/mcp", host=host, transport_security=security
    )


def _results_or_note(items: list[ResponseItemT]) -> ResultsResponse[ResponseItemT]:
    if items:
        return ResultsResponse[ResponseItemT](results=items)
    return ResultsResponse[ResponseItemT](results=[], note=NO_RECORDS_MATCHED_NOTE)


def _utc_now() -> datetime:
    return datetime.now(UTC)
