"""The Strategy run loop: one grounding repair, then success or UNGROUNDED_OUTPUT."""

from contextlib import nullcontext
from types import SimpleNamespace, TracebackType
from typing import Any

import pytest
from agents import Runner, Usage

from app.agents.common.context import RunContext
from app.agents.common.intents import Intent
from app.agents.strategy import run as strategy_run
from app.agents.strategy.output import StrategyOutput
from app.agents.strategy.validation import UngroundedOutputError
from app.intelligence.models import RunStatus
from tests.strategy_samples import recommendation, strategy_output


class FakeMCP:
    def __init__(self, context: RunContext, url: str) -> None:
        context.retrieved_ids |= {"act_1", "cmp_marketing_eye"}
        context.skill_budget.loaded.append("pricing")

    async def __aenter__(self) -> "FakeMCP":
        return self

    async def __aexit__(
        self, *exc: type[BaseException] | BaseException | TracebackType | None
    ) -> None:
        return None


def fake_runner(monkeypatch: pytest.MonkeyPatch, outputs: list[StrategyOutput]) -> list[Any]:
    inputs: list[Any] = []

    async def run(agent: object, items: Any, **kwargs: object) -> SimpleNamespace:
        inputs.append((items, kwargs["max_turns"]))
        output = outputs[len(inputs) - 1]
        return SimpleNamespace(
            final_output_as=lambda _type: output,
            to_input_list=lambda: [{"role": "user", "content": "first"}],
            raw_responses=[object()] * 5,  # five model turns used
            context_wrapper=SimpleNamespace(usage=Usage(requests=1, total_tokens=10)),
        )

    monkeypatch.setattr(strategy_run, "RunMCPServer", FakeMCP)
    monkeypatch.setattr(strategy_run, "model_provider", nullcontext)
    monkeypatch.setattr(Runner, "run", run)
    return inputs


def context() -> RunContext:
    return RunContext(
        company_id="cmp_marketing_eye", session_id="ses_1", run_id="run_1", intent=Intent.CHAT
    )


async def test_grounded_answer_needs_no_repair(monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = fake_runner(monkeypatch, [strategy_output(recommendation(1, "act_1"))])
    outcome = await strategy_run.run_strategy(context(), "What should we post?")
    assert outcome.status is RunStatus.SUCCEEDED
    assert len(inputs) == 1
    assert outcome.usage["total_tokens"] == 10


async def test_invented_id_is_repaired_once(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = strategy_output(recommendation(1, "act_invented"))
    good = strategy_output(recommendation(1, "act_1"))
    inputs = fake_runner(monkeypatch, [bad, good])
    outcome = await strategy_run.run_strategy(context(), "Plan a response")
    assert len(inputs) == 2
    repair_items, repair_turns = inputs[1]
    assert "act_invented" in repair_items[-1]["content"]
    assert repair_turns == 16 - 5  # the repair only gets the turns left
    assert outcome.usage["total_tokens"] == 20


async def test_second_ungrounded_answer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = strategy_output(recommendation(1, "act_invented"))
    fake_runner(monkeypatch, [bad, bad])
    with pytest.raises(UngroundedOutputError):
        await strategy_run.run_strategy(context(), "Plan a response")
