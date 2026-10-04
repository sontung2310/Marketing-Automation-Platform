"""Scenarios 4-A and 4-B: seeded database, real MCP, real OpenAI. Run with -m live.

Each run's stored document is written to evaluation/reports/ (gitignored) as evidence.
"""

import json
from functools import partial
from pathlib import Path

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


async def test_4a_response_plan_for_a_price_change(
    seeded_database: AsyncDatabase[Document],
) -> None:
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION,
        ref_id=BRIGHTLANE_PRICE_CHANGE,
        action=TriggerAction.RESPONSE_PLAN,
    )
    run = await run_live(seeded_database, trigger=trigger)
    save_evidence("4a_response_plan", run)

    assert run.status is RunStatus.SUCCEEDED, run.error
    tools = tool_names(run)
    assert tools[0] == "get_company_context"
    fetched = [c for c in run.tool_calls if c["tool"] == "get_competitor_activity"]
    assert any(BRIGHTLANE_PRICE_CHANGE in str(c["args_summary"]) for c in fetched)
    assert run.output is not None
    recommendations = run.output["recommendations"]
    assert isinstance(recommendations, list)
    assert 2 <= len(recommendations) <= 4
    responses = [r for r in recommendations if r["kind"] == "COMPETITIVE_RESPONSE"]
    assert any(BRIGHTLANE_PRICE_CHANGE in {e["id"] for e in r["evidence"]} for r in responses)
    assert all(r["next_action"] for r in recommendations if r["kind"] != "MONITOR")


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
