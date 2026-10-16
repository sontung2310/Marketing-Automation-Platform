"""Spend is logged even when the SDK raises mid-run (roadmap 8.3)."""

from types import SimpleNamespace

import pytest
from agents import AgentsException, Runner, Usage

from app.agents.common.context import RunContext
from app.agents.common.repair import run_counting_usage


async def test_usage_is_added_when_the_sdk_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    exc = AgentsException("boom")
    exc.run_data = SimpleNamespace(  # type: ignore[assignment]
        context_wrapper=SimpleNamespace(usage=Usage(requests=1, total_tokens=42))
    )

    async def fail(*args: object, **kwargs: object) -> None:
        raise exc

    monkeypatch.setattr(Runner, "run", fail)
    context = RunContext.__new__(RunContext)
    context.usage = Usage()
    with pytest.raises(AgentsException):
        await run_counting_usage(None, "hi", context=context)  # type: ignore[arg-type]
    assert context.usage.total_tokens == 42
