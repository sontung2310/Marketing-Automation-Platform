"""Runs over real HTTP (roadmap 6-C, 6-D), with stub agents so no model is called."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from pymongo.asynchronous.database import AsyncDatabase
from sse_starlette.sse import AppStatus

from app.agents.common.context import AgentOutcome, RunContext
from app.api.deps import get_run_service
from app.api.main import create_app
from app.core.db import Document, get_database
from app.intelligence.models import AgentName, RunStatus
from app.orchestration.references import RunRepositories
from app.orchestration.run_service import RunService
from evals.runtime import serve_app
from tests.execution_samples import execution_output
from tests.strategy_samples import recommendation, strategy_output

pytestmark = pytest.mark.integration
COMPANY = "cmp_marketing_eye"


async def planning_agent(context: RunContext, message: str | None) -> AgentOutcome:
    for label in ("Loading company context", "Searching competitor activity", "Drafting options"):
        context.emit("agent.step", {"label": label})
        await asyncio.sleep(0.3)  # long enough for the 202 to return first
    ref = str(context.trigger_context["id"]) if context.trigger_context else "act_1"
    return AgentOutcome(RunStatus.SUCCEEDED, strategy_output(recommendation(1, ref)))


async def drafting_agent(context: RunContext, message: str | None) -> AgentOutcome:
    context.emit("agent.step", {"label": "Drafting"})
    cited = (str(context.trigger_context["id"]),) if context.trigger_context else ()
    return AgentOutcome(RunStatus.SUCCEEDED, execution_output(evidence_ids=cited))


@pytest.fixture
async def api(seeded_database: AsyncDatabase[Document]) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    agents = {AgentName.STRATEGY: planning_agent, AgentName.EXECUTION: drafting_agent}
    app.dependency_overrides[get_database] = lambda: seeded_database
    app.dependency_overrides[get_run_service] = lambda: RunService(
        RunRepositories.for_database(seeded_database), agents
    )
    # sse-starlette flags shutdown process-wide; an earlier test's server exit would end
    # every later stream at once. One server per process in production, so test-only.
    AppStatus.should_exit = False
    async with (
        serve_app(app) as base_url,
        httpx.AsyncClient(base_url=base_url, timeout=30) as client,
    ):
        # Open the Mongo connections first, so timings measure the endpoint, not TLS setup.
        await asyncio.gather(*(client.get("/api/runs/run_warm") for _ in range(3)))
        yield client


async def activity_id(database: AsyncDatabase[Document], activity_type: str) -> str:
    activities = await RunRepositories.for_database(database).activities.search_for_company(
        COMPANY, detected_since=datetime(2000, 1, 1, tzinfo=UTC), limit=100
    )
    return next(a.id for a in activities if a.activity_type == activity_type)


async def read_events(
    client: httpx.AsyncClient, run_id: str, last_event_id: str | None = None
) -> list[dict[str, Any]]:
    headers = {"Last-Event-ID": last_event_id} if last_event_id else {}
    events: list[dict[str, Any]] = []
    async with client.stream("GET", f"/api/runs/{run_id}/events", headers=headers) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line.removeprefix("data: ")))
    return events


async def test_6c_feed_action_returns_202_fast_and_streams_in_order(
    api: httpx.AsyncClient, seeded_database: AsyncDatabase[Document]
) -> None:
    trigger = {
        "kind": "FEED_ACTION",
        "ref_id": await activity_id(seeded_database, "PRICE_CHANGE"),
        "action": "RESPONSE_PLAN",
    }
    started = time.perf_counter()
    response = await api.post("/api/runs", json={"trigger": trigger})
    elapsed = time.perf_counter() - started

    assert response.status_code == 202, response.text
    assert elapsed < 0.5
    accepted = response.json()
    assert (accepted["agent"], accepted["intent"]) == ("STRATEGY", "RESPONSE_PLAN")
    assert accepted["route"]["method"] == "DETERMINISTIC"

    events = await read_events(api, accepted["run_id"])
    types = [event["type"] for event in events]
    assert types[0] == "run.started"
    assert types.count("agent.step") == 3
    assert types[-2:] == ["output.final", "run.completed"]
    seqs = [event["seq"] for event in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert "recommendation_ids" in events[-2]["data"]


async def test_6d_reconnect_replays_after_last_event_id(
    api: httpx.AsyncClient, seeded_database: AsyncDatabase[Document]
) -> None:
    trigger = {
        "kind": "FEED_ACTION",
        "ref_id": await activity_id(seeded_database, "PRICE_CHANGE"),
        "action": "WHY_IT_MATTERS",
    }
    run_id = (await api.post("/api/runs", json={"trigger": trigger})).json()["run_id"]
    everything = await read_events(api, run_id)

    replay = await read_events(api, run_id, last_event_id="3")

    assert [e["seq"] for e in replay] == [e["seq"] for e in everything if e["seq"] > 3]


async def test_restored_session_can_still_approve(
    api: httpx.AsyncClient, seeded_database: AsyncDatabase[Document]
) -> None:
    trigger = {
        "kind": "FEED_ACTION",
        "ref_id": await activity_id(seeded_database, "NEW_BLOG"),
        "action": "CREATE_SIMILAR",
    }
    accepted = (await api.post("/api/runs", json={"trigger": trigger})).json()
    await read_events(api, accepted["run_id"])

    session = (await api.get(f"/api/sessions/{accepted['session_id']}")).json()
    [run] = session["runs"]
    assert run["status"] == "SUCCEEDED" and run["steps"] == [{"label": "Drafting"}]
    action_ids = run["output"]["proposed_action_ids"]
    assert action_ids and run["output"]["deliverable_id"]

    approved = await api.post(f"/api/actions/{action_ids[0]}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "EXECUTED"


async def test_invalid_requests_use_the_envelope(api: httpx.AsyncClient) -> None:
    trigger = {"kind": "FEED_ACTION", "ref_id": "act_missing", "action": "RESPONSE_PLAN"}
    both = await api.post("/api/runs", json={"message": "hi", "trigger": trigger})
    assert both.status_code == 422 and both.json()["error"]["code"] == "VALIDATION_ERROR"

    missing = await api.post("/api/runs", json={"trigger": trigger})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"

    for path in ("/api/runs/run_missing", "/api/runs/run_missing/events", "/api/sessions/ses_x"):
        assert (await api.get(path)).status_code == 404
