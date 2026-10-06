"""Trigger reference resolution and sessions against a seeded database."""

from datetime import UTC, datetime

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.common.context import AgentOutcome, RunContext
from app.core.config import get_settings
from app.core.db import Document
from app.core.errors import NotFoundError
from app.intelligence.models import AgentName, RunStatus
from app.orchestration.references import (
    RunRepositories,
    Unresolved,
    open_session,
    resolve_reference,
    resolve_trigger,
)
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import RunService
from evals.fixture import install_fixture, load_fixture, shifted_to
from evals.runtime import throwaway_database
from tests.execution_samples import execution_output
from tests.strategy_samples import recommendation, strategy_output

pytestmark = pytest.mark.integration
COMPANY = "cmp_marketing_eye"


async def test_feed_trigger_resolves_to_the_company_activity(
    seeded_database: AsyncDatabase[Document],
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    (activity,) = await repositories.activities.search_for_company(
        COMPANY, detected_since=datetime(2000, 1, 1, tzinfo=UTC), limit=1
    )
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id=activity.id, action=TriggerAction.RESPONSE_PLAN
    )
    record = await resolve_trigger(repositories, trigger, COMPANY)
    assert record["id"] == activity.id  # same key shape as MCP results


@pytest.mark.parametrize("company", [COMPANY, "cmp_someone_else"])
async def test_unknown_or_foreign_reference_is_not_found(
    seeded_database: AsyncDatabase[Document], company: str
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    (trend,) = await repositories.trends.search_for_company(COMPANY, limit=1)
    ref = "trd_missing" if company == COMPANY else trend.id
    trigger = Trigger(kind=TriggerKind.TREND, ref_id=ref, action=TriggerAction.USE_TREND)
    with pytest.raises(NotFoundError):
        await resolve_trigger(repositories, trigger, company)


async def test_sessions_are_created_then_reused_per_company(
    seeded_database: AsyncDatabase[Document],
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    created = await open_session(repositories, COMPANY, None)
    assert (await open_session(repositories, COMPANY, created.id)).id == created.id
    with pytest.raises(NotFoundError):
        await open_session(repositories, "cmp_someone_else", created.id)


async def test_eval_fixture_installs_shifted_to_now() -> None:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    fixture = load_fixture("intelligence_v2")
    async with throwaway_database("ma_fixture") as database:
        await install_fixture(database, shifted_to(fixture, datetime.now(UTC)))
        assert await database["competitor_activities"].count_documents({}) == len(
            fixture.competitor_activities
        )
        stale = await database["competitor_activities"].find_one({"_id": "act_fx_stale_01"})
        assert stale is not None and isinstance(stale["detected_at"], datetime)
        age = datetime.now(UTC) - stale["detected_at"]
        assert 60 <= age.days <= 80  # authored ~70 days before the snapshot


async def test_chat_references_resolve_against_the_session(
    seeded_database: AsyncDatabase[Document],
) -> None:
    repositories = RunRepositories.for_database(seeded_database)

    async def planning(context: RunContext, message: str | None) -> AgentOutcome:
        recs = [recommendation(n, "act_seed_001") for n in (1, 2, 3)]
        return AgentOutcome(RunStatus.SUCCEEDED, strategy_output(*recs))

    async def drafting(context: RunContext, message: str | None) -> AgentOutcome:
        return AgentOutcome(RunStatus.SUCCEEDED, execution_output(evidence_ids=()))

    service = RunService(
        repositories, {AgentName.STRATEGY: planning, AgentName.EXECUTION: drafting}
    )
    plan = await service.start(COMPANY, message="Plan our week", agent=AgentName.STRATEGY)
    session_id = plan.session_id

    second = await resolve_reference(repositories, "recommendation:2", session_id)
    assert isinstance(second, dict) and second["ordinal"] == 2
    assert second["run_id"] == plan.id
    seventh = await resolve_reference(repositories, "recommendation:7", session_id)
    assert seventh == Unresolved("No recommendation #7 in this session")

    assert await resolve_reference(repositories, "deliverable:last", session_id) == Unresolved(
        "No earlier deliverable in this session"
    )
    draft = await service.start(
        COMPANY, message="Write it", agent=AgentName.EXECUTION, session_id=session_id
    )
    last = await resolve_reference(repositories, "deliverable:last", session_id)
    assert isinstance(last, dict) and last["id"] == draft.persisted["deliverable_id"]

    assert await resolve_reference(repositories, "recommendation:1", None) == Unresolved(
        "No recommendation #1 in this session"
    )
