"""The eval runner over the real fixture and MCP, with a stub agent (no OpenAI)."""

from datetime import UTC, datetime

import pytest

from app.agents.common.context import AgentOutcome, RunContext
from app.core.config import get_settings
from app.intelligence.models import RunStatus
from app.orchestration.run_service import AgentFn
from evals.cases import GoldenCase
from evals.fixture import load_fixture
from evals.runner import run_suite
from tests.execution_samples import execution_output
from tests.strategy_samples import golden_case, recommendation, strategy_output

pytestmark = pytest.mark.integration


def stub_factory(mcp_url: str) -> AgentFn:
    async def agent(context: RunContext, message: str | None) -> AgentOutcome:
        assert mcp_url.endswith("/mcp")
        cited = str(context.trigger_context["id"]) if context.trigger_context else "act_seed_001"
        context.retrieved_ids.add(cited)
        output = strategy_output(recommendation(1, cited))
        return AgentOutcome(RunStatus.SUCCEEDED, output, {"total_tokens": 1})

    return agent


def golden(case_id: str, **input: object) -> GoldenCase:
    return golden_case(id=case_id, input=input)


async def test_runner_records_each_repeat_with_retrieved_ids() -> None:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    trigger = {"kind": "FEED_ACTION", "ref_id": "act_fx_inject_02", "action": "RESPONSE_PLAN"}
    history = [strategy_output(recommendation(1, "act_seed_001")).model_dump(mode="json")]
    cases = [
        golden("ST-TRIGGER", trigger=trigger),
        golden("ST-FOLLOWUP", message="Drop #1", session_history=history),
    ]
    records = await run_suite(
        "strategy",
        cases,
        load_fixture("intelligence_v2"),
        now=datetime.now(UTC),
        repeats=2,
        agent_factory=stub_factory,
    )

    assert sorted((r.case_id, r.repeat) for r in records) == [
        ("ST-FOLLOWUP", 1),
        ("ST-FOLLOWUP", 2),
        ("ST-TRIGGER", 1),
        ("ST-TRIGGER", 2),
    ]
    for record in records:
        assert record.error is None and record.run is not None
        assert record.run.status is RunStatus.SUCCEEDED
    trigger_record = next(r for r in records if r.case_id == "ST-TRIGGER")
    assert "act_fx_inject_02" in trigger_record.retrieved_ids
    follow_up = next(r for r in records if r.case_id == "ST-FOLLOWUP")
    assert "act_seed_001" in follow_up.retrieved_ids  # reused from the seeded history


def drafting_factory(mcp_url: str) -> AgentFn:
    async def agent(context: RunContext, message: str | None) -> AgentOutcome:
        trigger = context.trigger_context or {}
        cited = (str(trigger["id"]),) if trigger else ()
        output = execution_output(evidence_ids=cited)
        return AgentOutcome(RunStatus.SUCCEEDED, output, {"total_tokens": 1})

    return agent


async def test_execution_suite_resolves_history_refs_and_revisions() -> None:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    strategy_history = [
        strategy_output(
            recommendation(1, "act_seed_001"), recommendation(2, "act_seed_006")
        ).model_dump(mode="json")
    ]
    execution_history = [execution_output().model_dump(mode="json")]
    do_this = {"kind": "RECOMMENDATION", "ref_id": "history:2", "action": "DO_THIS"}
    similar = {"kind": "FEED_ACTION", "ref_id": "act_seed_006", "action": "CREATE_SIMILAR"}
    cases = [
        golden_case(
            id="EX-REC",
            suite="execution",
            input={"trigger": do_this, "session_history": strategy_history},
        ),
        golden_case(id="EX-SIM", suite="execution", input={"trigger": similar}),
        golden_case(
            id="EX-REVISE",
            suite="execution",
            input={
                "message": "Make it shorter",
                "agent_hint": "EXECUTION",
                "session_history": execution_history,
            },
        ),
    ]
    records = await run_suite(
        "execution",
        cases,
        load_fixture("intelligence_v2"),
        now=datetime.now(UTC),
        repeats=1,
        agent_factory=drafting_factory,
    )

    by_case = {r.case_id: r for r in records}
    for record in records:
        assert record.error is None and record.run is not None, record.error
        assert record.run.agent == "EXECUTION" and record.run.status is RunStatus.SUCCEEDED
    rec_run = by_case["EX-REC"].run
    assert rec_run is not None and str(rec_run.trigger["ref_id"]).startswith("rec_")
    # Recommendation 2's evidence is citable because the trigger carries it (5-C).
    assert "act_seed_006" in by_case["EX-REC"].retrieved_ids
    final = next(e for e in rec_run.events if e["type"] == "output.final")
    assert final["data"]["deliverable_id"] and final["data"]["proposed_action_ids"]
