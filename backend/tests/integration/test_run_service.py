"""Run service persistence and event log, with stub agents (no model calls)."""

import asyncio
from datetime import UTC, datetime

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.common.context import AgentOutcome, RunContext
from app.core.db import Document
from app.core.errors import NotFoundError, UpstreamUnavailableError, ValidationError
from app.intelligence.models import AgentName, Run, RunStatus
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import AgentFn, RunService
from tests.strategy_samples import recommendation, strategy_output

pytestmark = pytest.mark.integration
COMPANY = "cmp_marketing_eye"


async def answering_agent(context: RunContext, message: str | None) -> AgentOutcome:
    if context.trigger_context is not None:
        assert str(context.trigger_context["id"]) in context.retrieved_ids
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
    assert {event["run_id"] for event in stored.events} == {run.id}
    assert all("ts" in event for event in stored.events)
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
    session = await RunRepositories.for_database(seeded_database).sessions.get(run.session_id)
    assert session is not None and session.last_run_id is None  # a failure keeps the last answer


async def test_cancelled_run_is_finalised(seeded_database: AsyncDatabase[Document]) -> None:
    started = asyncio.Event()

    async def slow_agent(context: RunContext, message: str | None) -> AgentOutcome:
        started.set()
        await asyncio.sleep(60)
        raise AssertionError("unreachable")

    trigger = await price_change_trigger(seeded_database)
    task = asyncio.create_task(service(seeded_database, slow_agent).start(COMPANY, trigger=trigger))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    (document,) = await seeded_database["runs"].find().to_list()
    stored = Run.model_validate(document)
    assert stored.status is RunStatus.FAILED
    assert stored.error is not None and stored.error["code"] == "CANCELLED"
    assert stored.events[-1]["type"] == "run.failed"
    assert stored.finished_at is not None


async def test_unavailable_agent_and_other_company_persist_nothing(
    seeded_database: AsyncDatabase[Document],
) -> None:
    strategy_only = RunService(
        RunRepositories.for_database(seeded_database), {AgentName.STRATEGY: answering_agent}
    )
    with pytest.raises(ValidationError):
        await strategy_only.start(COMPANY, message="Write a post", agent=AgentName.EXECUTION)
    with pytest.raises(ValidationError):
        await strategy_only.start("cmp_other", message="Hi", agent=AgentName.STRATEGY)
    assert await seeded_database["runs"].count_documents({}) == 0
    assert await seeded_database["sessions"].count_documents({}) == 0


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


async def test_follow_up_reuses_evidence_and_supersedes_old_recommendations(
    seeded_database: AsyncDatabase[Document],
) -> None:
    retrieved: list[set[str]] = []

    async def recording_agent(context: RunContext, message: str | None) -> AgentOutcome:
        retrieved.append(set(context.retrieved_ids))
        return await answering_agent(context, message)

    runs = service(seeded_database, recording_agent)
    first = await runs.start(COMPANY, message="What should we post?", agent=AgentName.STRATEGY)
    second = await runs.start(
        COMPANY, message="Drop #2", agent=AgentName.STRATEGY, session_id=first.session_id
    )
    assert retrieved[1] >= {"act_1", "act_2"}  # cited by the first answer
    statuses = {
        doc["run_id"]: doc["status"]
        async for doc in seeded_database["recommendations"].find({}, {"run_id": 1, "status": 1})
    }
    assert statuses == {first.id: "SUPERSEDED", second.id: "OPEN"}


async def test_only_a_successful_answer_replaces_the_last_one(
    seeded_database: AsyncDatabase[Document],
) -> None:
    async def clarifying_agent(context: RunContext, message: str | None) -> AgentOutcome:
        output = strategy_output().model_copy(update={"status": "NEEDS_CLARIFICATION"})
        return AgentOutcome(RunStatus.NEEDS_CLARIFICATION, output, {})

    first = await service(seeded_database, answering_agent).start(
        COMPANY, message="What should we post?", agent=AgentName.STRATEGY
    )
    await service(seeded_database, clarifying_agent).start(
        COMPANY, message="LinkedIn", agent=AgentName.STRATEGY, session_id=first.session_id
    )
    session = await RunRepositories.for_database(seeded_database).sessions.get(first.session_id)
    assert session is not None and session.last_run_id == first.id


async def test_an_empty_answer_supersedes_and_a_failed_supersede_leaves_no_set(
    seeded_database: AsyncDatabase[Document],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def empty_agent(context: RunContext, message: str | None) -> AgentOutcome:
        return AgentOutcome(RunStatus.SUCCEEDED, strategy_output(), {})

    first = await service(seeded_database, answering_agent).start(
        COMPANY, message="What should we post?", agent=AgentName.STRATEGY
    )
    await service(seeded_database, empty_agent).start(
        COMPANY, message="Drop #1 and #2", agent=AgentName.STRATEGY, session_id=first.session_id
    )
    recs = seeded_database["recommendations"]
    assert await recs.count_documents({"run_id": first.id, "status": "OPEN"}) == 0

    async def broken(*args: object, **kwargs: object) -> None:
        raise ConnectionError("Mongo blip")

    repositories = RunRepositories.for_database(seeded_database)
    monkeypatch.setattr(repositories.recommendations, "supersede_open", broken)
    failed = await RunService(repositories, {AgentName.STRATEGY: answering_agent}).start(
        COMPANY, message="What should we post?", agent=AgentName.STRATEGY
    )
    assert failed.status is RunStatus.FAILED
    assert await recs.count_documents({"run_id": failed.id}) == 0


async def test_do_this_can_cite_the_recommendation_evidence(
    seeded_database: AsyncDatabase[Document],
) -> None:
    retrieved: list[set[str]] = []

    async def recording_agent(context: RunContext, message: str | None) -> AgentOutcome:
        retrieved.append(set(context.retrieved_ids))
        return await answering_agent(context, message)

    runs = service(seeded_database, recording_agent)
    strategy = await runs.start(COMPANY, message="What should we post?", agent=AgentName.STRATEGY)
    final = next(e for e in strategy.events if e["type"] == "output.final")
    second = final["data"]["recommendation_ids"][1]
    trigger = Trigger(kind=TriggerKind.RECOMMENDATION, ref_id=second, action=TriggerAction.DO_THIS)
    await runs.start(COMPANY, trigger=trigger)  # a new session: only the trigger grounds it
    assert retrieved[1] >= {second, "act_2"}
    assert "act_1" not in retrieved[1]  # recommendation 1's evidence is not this trigger's
