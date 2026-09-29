"""Run service persistence and event log, with stub agents (no model calls)."""

from datetime import UTC, datetime

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.common.context import AgentOutcome, RunContext
from app.core.db import Document
from app.core.errors import NotFoundError, UpstreamUnavailableError
from app.intelligence.models import AgentName, RunStatus
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import AgentFn, RunService
from tests.strategy_samples import recommendation, strategy_output

pytestmark = pytest.mark.integration
COMPANY = "cmp_marketing_eye"


async def answering_agent(context: RunContext, message: str | None) -> AgentOutcome:
    context.emit("agent.step", {"label": "Thinking"})
    output = strategy_output(recommendation(1, "act_1"), recommendation(2, "act_2"))
    return AgentOutcome(RunStatus.SUCCEEDED, output, {"total_tokens": 1})


async def failing_agent(context: RunContext, message: str | None) -> AgentOutcome:
    raise UpstreamUnavailableError("MCP is down")


def service(database: AsyncDatabase[Document], agent: AgentFn) -> RunService:
    agents = {AgentName.STRATEGY: agent, AgentName.EXECUTION: agent}
    return RunService(RunRepositories.for_database(database), agents)


async def price_change_trigger(database: AsyncDatabase[Document]) -> Trigger:
    repositories = RunRepositories.for_database(database)
    activities = await repositories.activities.search_for_company(
        COMPANY, detected_since=datetime(2000, 1, 1, tzinfo=UTC), limit=100
    )
    activity = next(a for a in activities if a.activity_type == "PRICE_CHANGE")
    return Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id=activity.id, action=TriggerAction.RESPONSE_PLAN
    )


async def test_completed_run_is_persisted_with_ordered_events(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = await price_change_trigger(seeded_database)
    run = await service(seeded_database, answering_agent).start(COMPANY, trigger=trigger)

    stored = await RunRepositories.for_database(seeded_database).runs.get(run.id)
    assert stored is not None
    assert (stored.agent, stored.intent, stored.status) == (
        AgentName.STRATEGY,
        "RESPONSE_PLAN",
        RunStatus.SUCCEEDED,
    )
    assert stored.route["method"] == "DETERMINISTIC"
    types = [event["type"] for event in stored.events]
    assert types == ["run.started", "agent.step", "output.final", "run.completed"]
    seqs = [event["seq"] for event in stored.events]
    assert seqs == list(range(1, len(seqs) + 1))
    assert stored.output is not None and stored.output["answer"] == "Respond on value, not price."
    recommendations = await seeded_database["recommendations"].find({"run_id": run.id}).to_list()
    assert {r["ordinal"] for r in recommendations} == {1, 2}
    final = next(e for e in stored.events if e["type"] == "output.final")
    data = final["data"]
    assert isinstance(data, dict)
    assert set(data["recommendation_ids"]) == {r["_id"] for r in recommendations}
    assert stored.finished_at is not None
    session = await RunRepositories.for_database(seeded_database).sessions.get(stored.session_id)
    assert session is not None and session.last_run_id == run.id


async def test_failed_run_records_the_failure(seeded_database: AsyncDatabase[Document]) -> None:
    trigger = await price_change_trigger(seeded_database)
    run = await service(seeded_database, failing_agent).start(COMPANY, trigger=trigger)

    assert run.status is RunStatus.FAILED
    assert run.error == {"code": "UPSTREAM_UNAVAILABLE", "message": "MCP is down"}
    assert run.events[-1]["type"] == "run.failed"
    assert await seeded_database["recommendations"].count_documents({"run_id": run.id}) == 0


async def test_unknown_reference_persists_nothing(seeded_database: AsyncDatabase[Document]) -> None:
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id="act_missing", action=TriggerAction.WHY_IT_MATTERS
    )
    with pytest.raises(NotFoundError):
        await service(seeded_database, answering_agent).start(COMPANY, trigger=trigger)
    assert await seeded_database["runs"].count_documents({}) == 0
    assert await seeded_database["sessions"].count_documents({}) == 0


async def test_chat_runs_with_the_selected_agent(seeded_database: AsyncDatabase[Document]) -> None:
    seen: list[dict[str, object] | None] = []

    async def remembering_agent(context: RunContext, message: str | None) -> AgentOutcome:
        seen.append(context.previous_output)
        return await answering_agent(context, message)

    runs = service(seeded_database, remembering_agent)
    first = await runs.start(COMPANY, message="What should we post?", agent=AgentName.STRATEGY)
    assert (first.intent, first.route["method"]) == ("CHAT", "EXPLICIT")
    await runs.start(
        COMPANY, message="Only LinkedIn", agent=AgentName.STRATEGY, session_id=first.session_id
    )
    assert seen[0] is None
    assert seen[1] is not None and seen[1]["answer"] == "Respond on value, not price."
