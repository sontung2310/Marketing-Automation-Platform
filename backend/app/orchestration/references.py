"""Resolve a trigger's ref_id to a company-scoped record, and open the run's session."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel

from app.core.db import Database
from app.core.errors import NotFoundError
from app.intelligence.models import Session
from app.intelligence.repositories import (
    CompetitorActivitiesRepository,
    InfluencersRepository,
    RecommendationsRepository,
    RunsRepository,
    SessionsRepository,
    TrendsRepository,
)
from app.orchestration.routing import Trigger, TriggerKind


@dataclass(frozen=True)
class RunRepositories:
    activities: CompetitorActivitiesRepository
    trends: TrendsRepository
    influencers: InfluencersRepository
    recommendations: RecommendationsRepository
    sessions: SessionsRepository
    runs: RunsRepository

    @classmethod
    def for_database(cls, database: Database) -> "RunRepositories":
        return cls(
            activities=CompetitorActivitiesRepository(database),
            trends=TrendsRepository(database),
            influencers=InfluencersRepository(database),
            recommendations=RecommendationsRepository(database),
            sessions=SessionsRepository(database),
            runs=RunsRepository(database),
        )


Resolver = Callable[[RunRepositories, str, str], Awaitable[BaseModel | None]]

RESOLVERS: dict[TriggerKind, Resolver] = {
    TriggerKind.FEED_ACTION: lambda r, ref, cmp: r.activities.get_for_company(ref, cmp),
    TriggerKind.TREND: lambda r, ref, cmp: r.trends.get_for_company(ref, cmp),
    TriggerKind.INFLUENCER: lambda r, ref, cmp: r.influencers.get_for_company(ref, cmp),
    TriggerKind.RECOMMENDATION: lambda r, ref, cmp: r.recommendations.get_for_company(ref, cmp),
}


async def resolve_trigger(
    repositories: RunRepositories, trigger: Trigger, company_id: str
) -> dict[str, object]:
    """The referenced record as JSON-ready data, or NotFoundError for this company."""
    record = await RESOLVERS[trigger.kind](repositories, trigger.ref_id, company_id)
    if record is None:
        raise NotFoundError(f"{trigger.ref_id} was not found", {"ref_id": trigger.ref_id})
    # `id` (not `_id`), the same shape the MCP tools return, so the model cites it as-is.
    return record.model_dump(mode="json")


async def open_session(
    repositories: RunRepositories, company_id: str, session_id: str | None
) -> Session:
    """Continue the company's session, or start a new one when none is given."""
    if session_id is None:
        session = Session(id=Session.new_id(), company_id=company_id, created_at=datetime.now(UTC))
        await repositories.sessions.upsert(session)
        return session
    existing = await repositories.sessions.get(session_id)
    if existing is None or existing.company_id != company_id:
        raise NotFoundError(f"{session_id} was not found", {"session_id": session_id})
    return existing
