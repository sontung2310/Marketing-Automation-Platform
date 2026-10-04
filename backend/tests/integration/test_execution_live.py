"""Scenarios 5-A and 5-B: seeded database, real MCP, real OpenAI. Run with -m live.

Each run's stored document is written to evaluation/reports/ (gitignored) as evidence.
"""

import json
import re
from functools import partial
from pathlib import Path

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.agents.execution.guards import longest_shared_run
from app.agents.execution.run import run_execution
from app.core.db import Document
from app.intelligence.models import AgentName, Run, RunStatus
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from app.orchestration.run_service import AgentFn, RunService
from evals.runtime import serve_mcp

pytestmark = pytest.mark.live
COMPANY = "cmp_marketing_eye"
BRIGHTLANE_BLOG = "act_seed_001"
BRIGHTLANE_CEO_LINKEDIN = "act_seed_011"
REPORTS = Path(__file__).resolve().parents[3] / "evaluation" / "reports"
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|my|me)\b")


def save_evidence(name: str, run: Run) -> None:
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"live_{name}.json"
    path.write_text(json.dumps(run.model_dump(mode="json"), indent=2), encoding="utf-8")


async def create_similar(database: AsyncDatabase[Document], activity_id: str) -> Run:
    repositories = RunRepositories.for_database(database)
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id=activity_id, action=TriggerAction.CREATE_SIMILAR
    )
    async with serve_mcp(database, COMPANY) as mcp_url:
        agents: dict[AgentName, AgentFn] = {
            AgentName.EXECUTION: partial(run_execution, mcp_url=mcp_url)
        }
        return await RunService(repositories, agents).start(COMPANY, trigger=trigger)


def deliverable_of(run: Run) -> dict[str, object]:
    assert run.status is RunStatus.SUCCEEDED, run.error
    assert run.output is not None and isinstance(run.output["deliverable"], dict)
    assert run.tool_calls[0]["tool"] == "get_company_context"
    return run.output["deliverable"]


async def stored_deliverable(database: AsyncDatabase[Document], run: Run) -> Document:
    stored = await database["deliverables"].find({"run_id": run.id}).to_list()
    assert len(stored) == 1
    return stored[0]


async def test_5a_create_a_similar_blog(seeded_database: AsyncDatabase[Document]) -> None:
    source = await seeded_database["competitor_activities"].find_one({"_id": BRIGHTLANE_BLOG})
    assert source is not None and source["content_excerpt"]
    run = await create_similar(seeded_database, BRIGHTLANE_BLOG)
    save_evidence("5a_similar_blog", run)

    deliverable = deliverable_of(run)
    body = str(deliverable["body_markdown"])
    assert deliverable["type"] == "BLOG_DRAFT"
    assert 800 <= len(body.split()) <= 1500
    for text in (source["title"], source["content_excerpt"]):
        assert longest_shared_run(body, str(text)) < 12
    assert not re.search(r"\bBrightlane\b", body, re.IGNORECASE)
    assert (await stored_deliverable(seeded_database, run))["type"] == "BLOG_DRAFT"


async def test_5b_draft_a_ceo_post(seeded_database: AsyncDatabase[Document]) -> None:
    run = await create_similar(seeded_database, BRIGHTLANE_CEO_LINKEDIN)
    save_evidence("5b_ceo_post", run)

    deliverable = deliverable_of(run)
    body = str(deliverable["body_markdown"])
    assert deliverable["type"] == "CEO_POST"
    assert len(body) <= 3000
    assert "Morgan Hale" in str(deliverable["author_persona"])
    assert FIRST_PERSON.search(body)
    assert "Maya Chen" not in body  # never speaks as the competitor's CEO
    assert (await stored_deliverable(seeded_database, run))["type"] == "CEO_POST"
