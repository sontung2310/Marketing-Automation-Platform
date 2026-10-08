"""Scenarios 4-B, 7b-C and 7b-D: seeded database, real MCP, real OpenAI. Run with -m live.

Each run's stored document is written to evaluation/reports/ (gitignored) as evidence.
"""

import json
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.strategy.run import run_strategy
from app.core.db import Document
from app.intelligence.models import AgentName, Run, RunStatus
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import AgentFn, RunService
from evals.runtime import serve_mcp

pytestmark = pytest.mark.live
COMPANY = "cmp_marketing_eye"
BRIGHTLANE_PRICE_CHANGE = "act_seed_026"
REPORTS = Path(__file__).resolve().parents[3] / "evaluation" / "reports"


def tool_names(run: Run) -> list[str]:
    return [str(call["tool"]) for call in run.tool_calls]


def cited_ids(run: Run) -> set[str]:
    assert run.output is not None
    recommendations = run.output["recommendations"]
    assert isinstance(recommendations, list)
    return {e["id"] for rec in recommendations for e in rec["evidence"]}


def save_evidence(name: str, run: Run) -> None:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"live_{name}.json"
    path.write_text(json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf-8")


async def run_live(
    database: AsyncDatabase[Document],
    *,
    trigger: Trigger | None = None,
    message: str | None = None,
) -> Run:
    repositories = RunRepositories.for_database(database)
    async with serve_mcp(database, COMPANY) as mcp_url:
        agents: dict[AgentName, AgentFn] = {
            AgentName.STRATEGY: partial(run_strategy, mcp_url=mcp_url)
        }
        return await RunService(repositories, agents).start(
            COMPANY, trigger=trigger, message=message, agent=AgentName.STRATEGY
        )


async def assert_niche(database: AsyncDatabase[Document], run: Run) -> list[dict[str, Any]]:
    """1-5 recommendations; each non-MONITOR one combines signals and names insight/audience."""
    assert run.status is RunStatus.SUCCEEDED, run.error
    assert run.output is not None
    recommendations = run.output["recommendations"]
    assert isinstance(recommendations, list)
    assert 1 <= len(recommendations) <= 5
    for rec in recommendations:
        if rec["kind"] == "MONITOR":
            continue
        assert rec["insight"].strip() and rec["audience"].strip()
        assert rec["next_action"]
        signals = {e["id"] for e in rec["evidence"] if e["kind"] != "company"}
        assert len(signals) >= 2, rec
        if all(i.startswith("act_") for i in signals):
            docs = await database["competitor_activities"].find({"_id": {"$in": list(signals)}})
            competitors = {doc["competitor_id"] async for doc in docs}
            assert len(competitors) >= 2, rec
    return recommendations


async def test_7b_c_generate_strategy_returns_a_niche_set(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = Trigger(
        kind=TriggerKind.COMPANY, ref_id=COMPANY, action=TriggerAction.GENERATE_STRATEGY
    )
    run = await run_live(seeded_database, trigger=trigger)
    save_evidence("7b_c_generate_strategy", run)

    assert run.intent == "STRATEGY_SYNTHESIS"
    tools = tool_names(run)
    assert tools[0] == "get_company_context"
    assert {"search_trends", "search_influencers"} <= set(tools)
    assert {"summarize_competitor_activity", "search_competitor_activity"} & set(tools)
    await assert_niche(seeded_database, run)


async def test_7b_d_plan_a_response_focuses_on_the_price_change(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION,
        ref_id=BRIGHTLANE_PRICE_CHANGE,
        action=TriggerAction.RESPONSE_PLAN,
    )
    run = await run_live(seeded_database, trigger=trigger)
    save_evidence("7b_d_price_focus", run)

    assert run.intent == "STRATEGY_SYNTHESIS"
    assert tool_names(run)[0] == "get_company_context"
    fetched = [c for c in run.tool_calls if c["tool"] == "get_competitor_activity"]
    assert any(BRIGHTLANE_PRICE_CHANGE in str(c["args_summary"]) for c in fetched)
    assert run.output is not None and run.output["implications"]
    await assert_niche(seeded_database, run)


async def test_4b_topics_for_next_week_are_persisted(
    seeded_database: AsyncDatabase[Document],
) -> None:
    run = await run_live(seeded_database, message="What should we post about next week?")
    save_evidence("4b_topics", run)

    assert run.status is RunStatus.SUCCEEDED, run.error
    assert run.output is not None
    recommendations = run.output["recommendations"]
    assert isinstance(recommendations, list)
    assert 1 <= len(recommendations) <= 5
    assert {r["kind"] for r in recommendations} == {"CONTENT_TOPIC"}
    await assert_niche(seeded_database, run)
    for rec in recommendations:
        assert any(e["id"].startswith(("trd_", "act_")) for e in rec["evidence"])
    for evidence_id in cited_ids(run):
        collection = {"trd": "trends", "act": "competitor_activities"}.get(evidence_id[:3])
        if collection:
            assert await seeded_database[collection].count_documents({"_id": evidence_id}) == 1
    stored = await seeded_database["recommendations"].find({"run_id": run.id}).to_list()
    assert sorted(int(str(doc["ordinal"])) for doc in stored) == list(
        range(1, len(recommendations) + 1)
    )
