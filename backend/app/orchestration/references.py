"""Resolve a trigger's ref_id to a company-scoped record, and open the run's session."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel

from app.core.db import Database
from app.core.errors import NotFoundError
from app.intelligence.models import AgentName, Run, Session
from app.intelligence.repositories import (
    CompetitorActivitiesRepository,
    DeliverablesRepository,
    InfluencersRepository,
    ProposedActionsRepository,
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
    deliverables: DeliverablesRepository
    proposed_actions: ProposedActionsRepository
    sessions: SessionsRepository
    runs: RunsRepository

    @classmethod
    def for_database(cls, database: Database) -> "RunRepositories":
        return cls(
            activities=CompetitorActivitiesRepository(database),
            trends=TrendsRepository(database),
            influencers=InfluencersRepository(database),
            recommendations=RecommendationsRepository(database),
            deliverables=DeliverablesRepository(database),
            proposed_actions=ProposedActionsRepository(database),
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
    repositories: RunRepositories, company_id: str, session_id: str | None, *, save: bool = True
) -> Session:
    """Continue the company's session, or start a new one when none is given.

    With save=False a new session is only built; the caller saves it once the run
    is certain to start, so a rejected request leaves no empty session behind.
    """
    if session_id is None:
        session = Session(id=Session.new_id(), company_id=company_id, created_at=datetime.now(UTC))
        if save:
            await repositories.sessions.upsert(session)
        return session
    existing = await repositories.sessions.get(session_id)
    if existing is None or existing.company_id != company_id:
        raise NotFoundError(f"{session_id} was not found", {"session_id": session_id})
    return existing


@dataclass(frozen=True)
class Unresolved:
    """A session reference with nothing behind it; the marketer is asked instead."""

    message: str


async def _recommendation(
    repositories: RunRepositories, runs: list[Run], value: str
) -> dict[str, object] | Unresolved:
    missing = Unresolved(f"No recommendation #{value} in this session")
    latest = next(
        (
            r
            for r in reversed(runs)
            if r.agent is AgentName.STRATEGY and r.persisted.get("recommendation_ids")
        ),
        None,
    )
    if latest is None or not value.isdigit():
        return missing
    record = await repositories.recommendations.get_by_ordinal(latest.id, int(value))
    return record.model_dump(mode="json") if record else missing


async def _deliverable(
    repositories: RunRepositories, runs: list[Run], value: str
) -> dict[str, object] | Unresolved:
    missing = Unresolved("No earlier deliverable in this session")
    ids = (
        r.persisted.get("deliverable_id") for r in reversed(runs) if r.agent is AgentName.EXECUTION
    )
    deliverable_id = next((str(i) for i in ids if i), None)
    if value != "last" or deliverable_id is None:
        return missing
    record = await repositories.deliverables.get(deliverable_id)
    return record.model_dump(mode="json") if record else missing


ReferenceResolver = Callable[
    [RunRepositories, list[Run], str], Awaitable[dict[str, object] | Unresolved]
]
# agents-spec §5.2: "recommendation:N" is the Nth recommendation of the session's latest
# Strategy run; "deliverable:last" is the session's latest deliverable.
REFERENCE_RESOLVERS: dict[str, ReferenceResolver] = {
    "recommendation": _recommendation,
    "deliverable": _deliverable,
}


async def resolve_reference(
    repositories: RunRepositories, reference: str, session_id: str | None
) -> dict[str, object] | Unresolved:
    """The record a chat reference points at, as the matching UI button would pass it."""
    kind, _, value = reference.partition(":")
    resolver = REFERENCE_RESOLVERS.get(kind)
    runs = await repositories.runs.list_for_session(session_id) if session_id else []
    if resolver is None:
        return Unresolved(f"I could not tell what {reference!r} refers to")
    return await resolver(repositories, runs, value)
