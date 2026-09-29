"""Start, route, run and persist one agent run (agents-spec §1). In-process; HTTP is Step 6."""

import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel

from app.agents.common.context import RunContext
from app.core.errors import DomainError, ValidationError
from app.intelligence.models import AgentName, Run, RunStatus
from app.orchestration.references import RunRepositories, open_session, resolve_trigger
from app.orchestration.routing import Route, Trigger, route_chat, route_trigger


@dataclass(frozen=True)
class AgentOutcome:
    status: RunStatus
    output: BaseModel
    usage: dict[str, object] = field(default_factory=dict)


# An agent receives the run context (trigger record included) and the chat message.
AgentFn = Callable[[RunContext, str | None], Awaitable[AgentOutcome]]


class RunService:
    def __init__(self, repositories: RunRepositories, agents: Mapping[AgentName, AgentFn]) -> None:
        self.repositories = repositories
        self.agents = agents

    async def start(
        self,
        company_id: str,
        *,
        trigger: Trigger | None = None,
        message: str | None = None,
        agent: AgentName | None = None,
        session_id: str | None = None,
    ) -> Run:
        if (trigger is None) == (message is None):
            raise ValidationError("Send exactly one of message or trigger")
        route, trigger_context = await self._route(company_id, trigger, agent)
        session = await open_session(self.repositories, company_id, session_id)
        previous = (
            await self.repositories.runs.get(session.last_run_id) if session.last_run_id else None
        )
        started = datetime.now(UTC)
        context = RunContext(
            company_id=company_id,
            session_id=session.id,
            run_id=Run.new_id(),
            intent=route.intent,
            trigger_context=trigger_context,
            previous_output=previous.output if previous else None,
        )
        run = Run(
            id=context.run_id,
            session_id=session.id,
            agent=route.agent,
            intent=route.intent,
            trigger=trigger.model_dump(mode="json") if trigger else {},
            route=route.model_dump(mode="json"),
            status=RunStatus.RUNNING,
            started_at=started,
        )
        await self.repositories.runs.upsert(run)
        context.emit(
            "run.started", {"agent": route.agent, "intent": route.intent, "route": run.route}
        )
        clock = time.monotonic()
        try:
            outcome = await self.agents[route.agent](context, message)
        except Exception as exc:
            code = exc.code if isinstance(exc, DomainError) else "AGENT_FAILED"
            context.emit("run.failed", {"code": code, "message": str(exc)})
            run = run.model_copy(
                update={"status": RunStatus.FAILED, "error": {"code": code, "message": str(exc)}}
            )
        else:
            output = outcome.output.model_dump(mode="json")
            context.emit("output.final", output)
            duration_ms = round((time.monotonic() - clock) * 1000)
            context.emit(
                "run.completed",
                {"status": outcome.status, "duration_ms": duration_ms, "usage": outcome.usage},
            )
            run = run.model_copy(
                update={"status": outcome.status, "output": output, "usage": outcome.usage}
            )
        run = run.model_copy(
            update={
                "events": context.events,
                "tool_calls": context.tool_calls,
                "skills_loaded": context.skill_budget.loaded,
                "finished_at": datetime.now(UTC),
            }
        )
        await self.repositories.runs.upsert(run)
        await self.repositories.sessions.upsert(session.model_copy(update={"last_run_id": run.id}))
        return run

    async def _route(
        self, company_id: str, trigger: Trigger | None, agent: AgentName | None
    ) -> tuple[Route, dict[str, object] | None]:
        if trigger is not None:
            route = route_trigger(trigger)
            return route, await resolve_trigger(self.repositories, trigger, company_id)
        if agent is None:
            raise ValidationError("Chat needs an explicit agent until the router exists (Step 6)")
        return route_chat(agent), None
