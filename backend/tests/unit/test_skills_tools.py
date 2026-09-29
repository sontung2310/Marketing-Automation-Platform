"""Scenarios 3-B and 3-C: allowlists, run budget and the load_skill tool."""

import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from app.agents.execution.config import SKILL_ALLOWLIST as EXECUTION
from app.agents.strategy.config import SKILL_ALLOWLIST as STRATEGY
from app.core.config import get_settings
from app.skills.integrity import read_lock
from app.skills.loader import PRODUCT_CONTEXT_NOTE, load_catalogue
from app.skills.tools import (
    SkillContent,
    SkillError,
    SkillErrorCode,
    SkillLoadBudget,
    load_skill,
    make_load_skill_tool,
    render_catalogue,
)


def test_allowlists_cover_exactly_the_vendored_catalogue() -> None:
    assert STRATEGY | EXECUTION == set(read_lock().skills) == set(load_catalogue())


@pytest.mark.parametrize("allowlist", [STRATEGY, EXECUTION])
def test_rendered_catalogue_lists_exactly_the_allowlist(allowlist: frozenset[str]) -> None:
    lines = render_catalogue(allowlist).splitlines()
    assert [line.split(":")[0].removeprefix("- ") for line in lines] == sorted(allowlist)


def test_execution_cannot_load_pricing_and_keeps_its_budget() -> None:
    budget = SkillLoadBudget()
    result = load_skill("pricing", None, allowlist=EXECUTION, budget=budget)
    assert isinstance(result, SkillError)
    assert result.code is SkillErrorCode.NOT_AVAILABLE
    assert "not available to this agent" in result.message
    assert budget.loaded == []


def test_loaded_skill_carries_the_product_context_note() -> None:
    result = load_skill("social", None, allowlist=STRATEGY, budget=SkillLoadBudget())
    assert isinstance(result, SkillContent)
    assert result.content.endswith(PRODUCT_CONTEXT_NOTE)
    assert result.description == load_catalogue()["social"].meta.description
    assert "references/platforms.md" in result.references


def test_fourth_successful_load_is_limit_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    budget = SkillLoadBudget()
    for name in ("social", "pricing", "competitors"):
        assert isinstance(load_skill(name, None, allowlist=STRATEGY, budget=budget), SkillContent)

    def fail(*_: object) -> None:
        raise AssertionError("no file may be read after the limit")

    monkeypatch.setattr("app.skills.tools.read_reference", fail)
    reference = "references/pricing-models.md"
    result = load_skill("pricing", reference, allowlist=STRATEGY, budget=budget)
    assert isinstance(result, SkillError)
    assert result.code is SkillErrorCode.LIMIT_REACHED


def test_invalid_reference_is_an_error_and_free() -> None:
    budget = SkillLoadBudget()
    result = load_skill("pricing", "../social/SKILL.md", allowlist=STRATEGY, budget=budget)
    assert isinstance(result, SkillError)
    assert result.code is SkillErrorCode.INVALID_REFERENCE
    assert budget.loaded == []


def test_oversized_content_is_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKILL_MAX_CHARS", "100")
    get_settings.cache_clear()
    try:
        result = load_skill("social", None, allowlist=STRATEGY, budget=SkillLoadBudget())
    finally:
        get_settings.cache_clear()
    assert isinstance(result, SkillContent)
    assert result.truncated
    assert "[Truncated at 100 characters.]" in result.content
    assert len(result.content) < 100 + 200


async def test_parallel_tool_calls_cannot_exceed_the_budget() -> None:
    budget = SkillLoadBudget()
    tool = make_load_skill_tool(STRATEGY, budget)
    ctx = ToolContext(context=None, tool_name="load_skill", tool_call_id="1", tool_arguments="")
    calls = [
        tool.on_invoke_tool(ctx, json.dumps({"name": name, "reference": None}))
        for name in sorted(STRATEGY)[:6]
    ]
    results = [json.loads(raw) for raw in await asyncio.gather(*calls)]
    assert len(budget.loaded) == 3
    assert [r.get("code") for r in results].count("LIMIT_REACHED") == 3


async def test_tool_returns_json_error_instead_of_raising() -> None:
    tool = make_load_skill_tool(EXECUTION, SkillLoadBudget())
    assert tool.name == "load_skill"
    ctx = ToolContext(context=None, tool_name="load_skill", tool_call_id="1", tool_arguments="")
    raw = await tool.on_invoke_tool(ctx, json.dumps({"name": "pricing", "reference": None}))
    assert json.loads(raw)["code"] == "NOT_AVAILABLE"
