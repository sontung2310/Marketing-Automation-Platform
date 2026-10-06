"""Agent runs and sessions (api-contract "Agent runs"). Validate, then delegate."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Request, status
from fastapi.responses import JSONResponse
from sse_starlette import EventSourceResponse

from app.api.deps import ClassifierDep, RunServiceDep, SettingsDep
from app.api.schemas.runs import AgentHint, RunRequest
from app.intelligence.models import AgentName
from app.orchestration import run_api

router = APIRouter(tags=["runs"])


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": run_api.RunAccepted},
        200: {"model": run_api.RouterAnswerView},
    },
)
async def start_run(
    body: RunRequest,
    service: RunServiceDep,
    classifier: ClassifierDep,
    settings: SettingsDep,
    tasks: BackgroundTasks,
) -> JSONResponse:
    hint = None if body.agent_hint is AgentHint.AUTO else AgentName(body.agent_hint)
    plan, reply = await run_api.start(
        service,
        classifier,
        settings.default_company_id,
        message=body.message,
        trigger=body.trigger,
        hint=hint,
        session_id=body.session_id,
    )
    if plan is None:  # the router answered; no run
        return JSONResponse(reply.model_dump(mode="json"), status_code=status.HTTP_200_OK)
    # Vercel keeps the function alive for background work (design.md, task 1.1 spike).
    tasks.add_task(service.execute, plan)
    return JSONResponse(reply.model_dump(mode="json"), status_code=status.HTTP_202_ACCEPTED)


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
