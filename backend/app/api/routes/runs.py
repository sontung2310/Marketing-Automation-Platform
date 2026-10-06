"""Agent runs and sessions (api-contract "Agent runs"). Validate, then delegate."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Request, status
from sse_starlette import EventSourceResponse

from app.api.deps import RunServiceDep, SettingsDep
from app.api.schemas.runs import AgentHint, RunRequest
from app.intelligence.models import AgentName
from app.orchestration import run_api

router = APIRouter(tags=["runs"])


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    body: RunRequest, service: RunServiceDep, settings: SettingsDep, tasks: BackgroundTasks
) -> run_api.RunAccepted:
    agent = None if body.agent_hint is AgentHint.AUTO else AgentName(body.agent_hint)
    plan = await service.prepare(
        settings.default_company_id,
        trigger=body.trigger,
        message=body.message,
        agent=agent,
        session_id=body.session_id,
    )
    # Vercel keeps the function alive for background work (design.md, task 1.1 spike).
    tasks.add_task(service.execute, plan)
    return run_api.accepted(plan.run)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, service: RunServiceDep) -> run_api.RunView:
    return run_api.run_view(await service.load(run_id))


@router.get("/runs/{run_id}/events")
async def run_events(
    run_id: str,
    request: Request,
    service: RunServiceDep,
    last_event_id: Annotated[str | None, Header(max_length=20)] = None,
) -> EventSourceResponse:
    await service.load(run_id)  # a missing run is a 404, not an empty stream
    events = run_api.run_events(
        service, run_id, last_event_id=last_event_id, is_disconnected=request.is_disconnected
    )
    return EventSourceResponse(events, ping=15)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str, service: RunServiceDep, settings: SettingsDep
) -> run_api.SessionView:
    return await run_api.session_view(service, session_id, settings.default_company_id)
