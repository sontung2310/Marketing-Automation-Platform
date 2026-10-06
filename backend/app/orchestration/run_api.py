"""Runs over HTTP (api-contract "Agent runs"): views, the live event stream, sessions."""

import asyncio
import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from time import monotonic

from pydantic import BaseModel

from app.agents.execution.run import run_execution
from app.agents.strategy.run import run_strategy
from app.core.errors import NotFoundError
from app.intelligence.models import AgentName, Run, RunStatus
from app.orchestration.run_service import AgentFn, RunService

# The agents a live run can reach (agents-spec §1).
RUN_AGENTS: dict[AgentName, AgentFn] = {
    AgentName.STRATEGY: run_strategy,
    AgentName.EXECUTION: run_execution,
}

STREAM_POLL_SECONDS = 0.5
# ponytail: serverless caps a function's duration, so the stream ends itself and the
# browser resumes with Last-Event-ID. Push events instead on a long-lived host.
STREAM_MAX_SECONDS = 55.0
STREAM_RETRY_MS = 1000
TERMINAL_EVENTS = {"run.completed", "run.failed"}


class RouteView(BaseModel):
    method: str
    reason: str
    confidence: float


class RunAccepted(BaseModel):
    run_id: str
    session_id: str
    agent: AgentName
    intent: str
    route: RouteView


class RunView(BaseModel):
    id: str
    session_id: str
    agent: AgentName
    intent: str
    message: str | None
    trigger: dict[str, object] | None
    route: RouteView
    status: RunStatus
    steps: list[dict[str, object]]
    tool_calls: list[dict[str, object]]
    skills_loaded: list[str]
    output: dict[str, object] | None
    error: dict[str, object] | None
    started_at: datetime
    finished_at: datetime | None


class SessionView(BaseModel):
    id: str
    runs: list[RunView]


def accepted(run: Run) -> RunAccepted:
    return RunAccepted(
        run_id=run.id,
        session_id=run.session_id,
        agent=run.agent,
        intent=run.intent,
        route=_route(run),
    )


def run_view(run: Run) -> RunView:
    return RunView(
        id=run.id,
        session_id=run.session_id,
        agent=run.agent,
        intent=run.intent,
        message=run.message,
        trigger=run.trigger or None,
        route=_route(run),
        status=run.status,
        steps=[e["data"] for e in run.events if e["type"] == "agent.step"],
        tool_calls=run.tool_calls,
        skills_loaded=run.skills_loaded,
        # The same payload as output.final, so restored cards can still approve.
        output=run.output | run.persisted if run.output is not None else None,
        error=run.error,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


async def session_view(service: RunService, session_id: str, company_id: str) -> SessionView:
    session = await service.repositories.sessions.get(session_id)
    if session is None or session.company_id != company_id:
        raise NotFoundError(f"{session_id} was not found", {"session_id": session_id})
    runs = await service.repositories.runs.list_for_session(session_id)
    return SessionView(id=session_id, runs=[run_view(run) for run in runs])


async def run_events(
    service: RunService,
    run_id: str,
    *,
    last_event_id: str | None,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_seconds: float = STREAM_POLL_SECONDS,
    max_seconds: float = STREAM_MAX_SECONDS,
) -> AsyncGenerator[dict[str, str | int]]:
    """The run's events after `Last-Event-ID` (their `seq`), live until the run ends."""
    await service.load(run_id)  # 404 before the stream opens
    sent = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0
    yield {"retry": STREAM_RETRY_MS, "comment": "run stream"}
    deadline = monotonic() + max_seconds
    while monotonic() < deadline and not await is_disconnected():
        run = await service.load(run_id)
        for event in run.events:
            seq = int(str(event["seq"]))
            if seq <= sent:
                continue
            sent = seq
            yield {"event": str(event["type"]), "id": str(seq), "data": _json(event)}
            if event["type"] in TERMINAL_EVENTS:
                return
        await asyncio.sleep(poll_seconds)


def _route(run: Run) -> RouteView:
    return RouteView(
        method=str(run.route.get("method", "DETERMINISTIC")),
        reason=str(run.route.get("reason", "")),
        confidence=float(str(run.route.get("confidence", 1.0))),
    )


def _json(event: dict[str, object]) -> str:
    return json.dumps(event, default=lambda value: value.isoformat())
