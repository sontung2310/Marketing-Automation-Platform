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
        load_fixture("intelligence_v1"),
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
