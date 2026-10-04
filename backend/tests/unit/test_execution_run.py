"""The Execution run loop: one contract repair, then success or a domain error."""

from contextlib import nullcontext
from types import SimpleNamespace, TracebackType
from typing import Any

import pytest
from agents import Runner, Usage

from app.agents.common.context import RunContext
from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.common.intents import Intent
from app.agents.execution import run as execution_run
from app.agents.execution.output import ExecutionOutput
from app.intelligence.models import DeliverableType, RunStatus
from tests.execution_samples import clarification, deliverable, execution_output


class FakeMCP:
    def __init__(self, context: RunContext, url: str) -> None:
        context.retrieved_ids |= {"act_1", "cmp_marketing_eye"}
        context.skill_budget.loaded.append("social")

    async def __aenter__(self) -> "FakeMCP":
        return self

    async def __aexit__(
        self, *exc: type[BaseException] | BaseException | TracebackType | None
    ) -> None:
        return None


def fake_runner(monkeypatch: pytest.MonkeyPatch, outputs: list[ExecutionOutput]) -> list[Any]:
    inputs: list[Any] = []

    async def run(agent: object, items: Any, **kwargs: object) -> SimpleNamespace:
        inputs.append(items)
        output = outputs[len(inputs) - 1]
        return SimpleNamespace(
            final_output_as=lambda _type: output,
            to_input_list=lambda: [{"role": "user", "content": "first"}],
            raw_responses=[object()] * 4,
            context_wrapper=SimpleNamespace(usage=Usage(requests=1, total_tokens=10)),
        )

    monkeypatch.setattr(execution_run, "RunMCPServer", FakeMCP)
    monkeypatch.setattr(execution_run, "model_provider", nullcontext)
    monkeypatch.setattr(Runner, "run", run)
    return inputs


def similar_post() -> RunContext:
    activity = {"id": "act_1", "activity_type": "SOCIAL_POST", "channel": "LINKEDIN"}
    return RunContext(
        company_id="cmp_marketing_eye",
        session_id="ses_1",
        run_id="run_1",
        intent=Intent.CREATE_SIMILAR,
        trigger_context=activity,
    )


async def test_valid_post_needs_no_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = fake_runner(monkeypatch, [execution_output()])
    outcome = await execution_run.run_execution(similar_post(), None)
    assert outcome.status is RunStatus.SUCCEEDED
    assert "Deliverable type: LINKEDIN_POST" in inputs[0]
    assert isinstance(outcome.output, ExecutionOutput) and outcome.output.deliverable
    assert outcome.output.deliverable.word_count == 9  # recounted in code


async def test_wrong_type_is_repaired_once(monkeypatch: pytest.MonkeyPatch) -> None:
    blog = execution_output(deliverable(DeliverableType.BLOG_DRAFT))
    inputs = fake_runner(monkeypatch, [blog, execution_output()])
    outcome = await execution_run.run_execution(similar_post(), None)
    assert len(inputs) == 2
    assert "must be a LINKEDIN_POST" in inputs[1][-1]["content"]
    assert outcome.usage["total_tokens"] == 20


async def test_a_second_wrong_type_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    blog = execution_output(deliverable(DeliverableType.BLOG_DRAFT))
    fake_runner(monkeypatch, [blog, blog])
    with pytest.raises(InvalidOutputError):
        await execution_run.run_execution(similar_post(), None)


async def test_a_second_ungrounded_answer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = execution_output(evidence_ids=("act_invented",))
    inputs = fake_runner(monkeypatch, [bad, bad])
    with pytest.raises(UngroundedOutputError):
        await execution_run.run_execution(similar_post(), None)
    assert "act_invented" in inputs[1][-1]["content"]


async def test_clarification_maps_to_its_run_status(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_runner(monkeypatch, [clarification()])
    ctx = similar_post()
    ctx.intent, ctx.trigger_context = Intent.CHAT, None
    outcome = await execution_run.run_execution(ctx, "Write it")
    assert outcome.status is RunStatus.NEEDS_CLARIFICATION
