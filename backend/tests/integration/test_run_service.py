"""Run service persistence and event log, with stub agents (no model calls)."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.common.context import AgentOutcome, RunContext
from app.core.db import Document
from app.core.errors import NotFoundError, UpstreamUnavailableError, ValidationError
from app.intelligence.models import AgentName, Run, RunStatus
from app.intelligence.repositories import ProposedActionsRepository
from app.orchestration import run_service
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import AgentFn, RunService
from tests.execution_samples import clarification, execution_output
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


async def drafting_agent(context: RunContext, message: str | None) -> AgentOutcome:
    cited = (str(context.trigger_context["id"]),) if context.trigger_context else ()
    return AgentOutcome(RunStatus.SUCCEEDED, execution_output(evidence_ids=cited))


def service(
    database: AsyncDatabase[Document], agent: AgentFn, execution: AgentFn = drafting_agent
) -> RunService:
    agents = {AgentName.STRATEGY: agent, AgentName.EXECUTION: execution}
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
        "STRATEGY_SYNTHESIS",
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
    assert all(r["insight"] and r["audience"] for r in recommendations)
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


async def test_an_empty_answer_keeps_the_set_and_a_failed_supersede_leaves_no_set(
    seeded_database: AsyncDatabase[Document],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def empty_agent(context: RunContext, message: str | None) -> AgentOutcome:
        return AgentOutcome(RunStatus.SUCCEEDED, strategy_output(), {})

    first = await service(seeded_database, answering_agent).start(
        COMPANY, message="What should we post?", agent=AgentName.STRATEGY
    )
    await service(seeded_database, empty_agent).start(
        COMPANY, message="What did Brightlane do?", agent=AgentName.STRATEGY
    )
    recs = seeded_database["recommendations"]
    # A factual answer recommends nothing, so the company's set is unchanged.
    assert await recs.count_documents({"run_id": first.id, "status": "OPEN"}) == 2

    async def broken(*args: object, **kwargs: object) -> None:
        raise ConnectionError("Mongo blip")

    repositories = RunRepositories.for_database(seeded_database)
    monkeypatch.setattr(repositories.recommendations, "supersede_open", broken)
    failed = await RunService(repositories, {AgentName.STRATEGY: answering_agent}).start(
        COMPANY, message="What should we post?", agent=AgentName.STRATEGY
    )
    assert failed.status is RunStatus.FAILED
    assert await recs.count_documents({"run_id": failed.id}) == 0


async def test_a_new_set_supersedes_another_sessions_set(
    seeded_database: AsyncDatabase[Document],
) -> None:
    runs = service(seeded_database, answering_agent)
    session_a = await runs.start(COMPANY, message="Plan our month", agent=AgentName.STRATEGY)
    session_b = await runs.start(COMPANY, message="What should we do?", agent=AgentName.STRATEGY)
    assert session_a.session_id != session_b.session_id
    statuses = {
        doc["run_id"]: doc["status"]
        async for doc in seeded_database["recommendations"].find({}, {"run_id": 1, "status": 1})
    }
    assert statuses == {session_a.id: "SUPERSEDED", session_b.id: "OPEN"}


async def recommendation_trigger(runs: RunService, ordinal: int) -> Trigger:
    strategy = await runs.start(COMPANY, message="What should we post?", agent=AgentName.STRATEGY)
    final = next(e for e in strategy.events if e["type"] == "output.final")
    rec_id = final["data"]["recommendation_ids"][ordinal - 1]
    return Trigger(kind=TriggerKind.RECOMMENDATION, ref_id=rec_id, action=TriggerAction.DO_THIS)


async def test_a_successful_do_this_marks_the_recommendation_done(
    seeded_database: AsyncDatabase[Document],
) -> None:
    runs = service(seeded_database, answering_agent)
    trigger = await recommendation_trigger(runs, 1)
    await runs.start(COMPANY, trigger=trigger)
    recs = seeded_database["recommendations"]
    assert (await recs.find_one({"_id": trigger.ref_id}) or {})["status"] == "DONE"
    others = await recs.find({"_id": {"$ne": trigger.ref_id}}, {"status": 1}).to_list()
    assert {doc["status"] for doc in others} == {"OPEN"}

    # "#2" in chat resolves to the same trigger context as the button.
    second = await recommendation_trigger(runs, 2)
    record = await RunRepositories.for_database(seeded_database).recommendations.get(second.ref_id)
    assert record is not None
    chat = run_service.ChatRoute(
        route=run_service.route_trigger(second).model_copy(update={"method": "CLASSIFIER"}),
        trigger_context=record.model_dump(mode="json"),
    )
    await runs.execute(await runs.prepare(COMPANY, message="Write #2", chat=chat))
    assert (await recs.find_one({"_id": second.ref_id}) or {})["status"] == "DONE"


async def test_a_failed_do_this_keeps_the_recommendation_open(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = await recommendation_trigger(service(seeded_database, answering_agent), 1)
    failed = await service(seeded_database, answering_agent, failing_agent).start(
        COMPANY, trigger=trigger
    )
    assert failed.status is RunStatus.FAILED
    stored = await seeded_database["recommendations"].find_one({"_id": trigger.ref_id})
    assert stored is not None and stored["status"] == "OPEN"


async def test_do_this_can_cite_the_recommendation_evidence(
    seeded_database: AsyncDatabase[Document],
) -> None:
    retrieved: list[set[str]] = []

    async def recording_agent(context: RunContext, message: str | None) -> AgentOutcome:
        retrieved.append(set(context.retrieved_ids))
        return await answering_agent(context, message)

    async def recording_drafter(context: RunContext, message: str | None) -> AgentOutcome:
        retrieved.append(set(context.retrieved_ids))
        return await drafting_agent(context, message)

    runs = service(seeded_database, recording_agent, recording_drafter)
    strategy = await runs.start(COMPANY, message="What should we post?", agent=AgentName.STRATEGY)
    final = next(e for e in strategy.events if e["type"] == "output.final")
    second = final["data"]["recommendation_ids"][1]
    trigger = Trigger(kind=TriggerKind.RECOMMENDATION, ref_id=second, action=TriggerAction.DO_THIS)
    await runs.start(COMPANY, trigger=trigger)  # a new session: only the trigger grounds it
    assert retrieved[1] >= {second, "act_2"}
    assert "act_1" not in retrieved[1]  # recommendation 1's evidence is not this trigger's


async def social_post_trigger(database: AsyncDatabase[Document]) -> Trigger:
    activities = await RunRepositories.for_database(database).activities.search_for_company(
        COMPANY, detected_since=datetime(2000, 1, 1, tzinfo=UTC), limit=100
    )
    activity = next(
        a for a in activities if a.activity_type == "SOCIAL_POST" and a.channel == "LINKEDIN"
    )
    return Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id=activity.id, action=TriggerAction.CREATE_SIMILAR
    )


async def test_execution_run_persists_its_deliverable(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = await social_post_trigger(seeded_database)
    run = await service(seeded_database, answering_agent).start(COMPANY, trigger=trigger)

    assert (run.agent, run.intent, run.status) == (
        AgentName.EXECUTION,
        "CREATE_SIMILAR",
        RunStatus.SUCCEEDED,
    )
    final = next(e for e in run.events if e["type"] == "output.final")
    stored = [doc async for doc in seeded_database["deliverables"].find({"run_id": run.id})]
    assert [doc["_id"] for doc in stored] == [final["data"]["deliverable_id"]]
    assert stored[0]["type"] == "LINKEDIN_POST"
    actions = [doc async for doc in seeded_database["proposed_actions"].find({})]
    assert [doc["_id"] for doc in actions] == final["data"]["proposed_action_ids"]
    assert actions[0]["status"] == "PROPOSED"
    assert actions[0]["payload"]["deliverable_id"] == stored[0]["_id"]
    assert final["data"]["proposed_actions"][0]["id"] == actions[0]["_id"]


async def test_execution_clarification_stores_nothing(
    seeded_database: AsyncDatabase[Document],
) -> None:
    async def asking_agent(context: RunContext, message: str | None) -> AgentOutcome:
        return AgentOutcome(RunStatus.NEEDS_CLARIFICATION, clarification())

    run = await service(seeded_database, answering_agent, asking_agent).start(
        COMPANY, message="Write it", agent=AgentName.EXECUTION
    )
    assert run.status is RunStatus.NEEDS_CLARIFICATION
    final = next(e for e in run.events if e["type"] == "output.final")
    assert final["data"]["deliverable_id"] is None
    assert await seeded_database["deliverables"].count_documents({}) == 0


async def test_a_failed_action_insert_leaves_no_deliverable(
    seeded_database: AsyncDatabase[Document], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken_insert(self: object, models: object) -> None:
        raise ConnectionError("write failed")

    monkeypatch.setattr(ProposedActionsRepository, "insert_many", broken_insert)
    trigger = await social_post_trigger(seeded_database)
    run = await service(seeded_database, answering_agent).start(COMPANY, trigger=trigger)

    assert run.status is RunStatus.FAILED
    assert await seeded_database["deliverables"].count_documents({}) == 0
    assert await seeded_database["proposed_actions"].count_documents({}) == 0


async def test_events_reach_mongo_while_the_agent_works(
    seeded_database: AsyncDatabase[Document],
) -> None:
    gate = asyncio.Event()

    async def slow_agent(context: RunContext, message: str | None) -> AgentOutcome:
        context.emit("agent.step", {"label": "Loading company context"})
        await gate.wait()
        return await answering_agent(context, message)

    runs = service(seeded_database, slow_agent)
    plan = await runs.prepare(COMPANY, trigger=await price_change_trigger(seeded_database))
    assert [e["type"] for e in await stored_events(seeded_database, plan.run.id)] == ["run.started"]

    execution = asyncio.create_task(runs.execute(plan))
    await asyncio.sleep(1.2)  # more than two writer flushes
    assert (await runs.load(plan.run.id)).status is RunStatus.RUNNING
    assert [e["type"] for e in await stored_events(seeded_database, plan.run.id)] == [
        "run.started",
        "agent.step",
    ]

    gate.set()
    run = await execution
    assert run.events[-1]["type"] == "run.completed"
    assert set(run.persisted) >= {"recommendation_ids"}


async def test_a_run_whose_worker_died_reads_as_interrupted(
    seeded_database: AsyncDatabase[Document],
) -> None:
    runs = service(seeded_database, answering_agent)
    plan = await runs.prepare(COMPANY, trigger=await price_change_trigger(seeded_database))
    await seeded_database["runs"].update_one(
        {"_id": plan.run.id}, {"$set": {"started_at": datetime.now(UTC) - timedelta(minutes=5)}}
    )

    run = await runs.load(plan.run.id)

    assert run.status is RunStatus.FAILED
    assert run.error == {"code": "INTERNAL", "message": "The run was interrupted"}
    assert run.events[-1]["type"] == "run.failed"
    settled = await runs.load(plan.run.id)
    settled_events = [(e["seq"], e["type"]) for e in settled.events]
    assert settled_events == [(1, "run.started"), (2, "run.failed")]
    with pytest.raises(NotFoundError):
        await runs.load("run_missing")


async def test_a_run_read_as_interrupted_stays_failed_when_its_worker_finishes(
    seeded_database: AsyncDatabase[Document],
) -> None:
    gate = asyncio.Event()

    async def slow_agent(context: RunContext, message: str | None) -> AgentOutcome:
        await gate.wait()
        return await answering_agent(context, message)

    runs = service(seeded_database, slow_agent)
    plan = await runs.prepare(COMPANY, trigger=await price_change_trigger(seeded_database))
    execution = asyncio.create_task(runs.execute(plan))
    await seeded_database["runs"].update_one(
        {"_id": plan.run.id}, {"$set": {"started_at": datetime.now(UTC) - timedelta(minutes=5)}}
    )
    assert (await runs.load(plan.run.id)).status is RunStatus.FAILED  # what the stream showed

    gate.set()
    finished = await execution

    assert finished.status is RunStatus.FAILED
    assert (await runs.load(plan.run.id)).events[-1]["type"] == "run.failed"


async def test_a_slow_agent_is_stopped_before_it_reads_as_lost(
    seeded_database: AsyncDatabase[Document], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_service, "RUN_TIMEOUT_SECONDS", 0.2)

    async def stuck_agent(context: RunContext, message: str | None) -> AgentOutcome:
        await asyncio.sleep(5)
        return await answering_agent(context, message)

    run = await service(seeded_database, stuck_agent).start(
        COMPANY, trigger=await price_change_trigger(seeded_database)
    )

    assert run.status is RunStatus.FAILED
    assert run.error == {"code": "CANCELLED", "message": "The run took too long and was stopped"}


async def stored_events(database: AsyncDatabase[Document], run_id: str) -> list[dict[str, object]]:
    run = await RunRepositories.for_database(database).runs.get(run_id)
    assert run is not None
    return run.events
