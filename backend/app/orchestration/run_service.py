"""Start, route, run and persist one agent run (agents-spec §1). In-process; HTTP is Step 6."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.errors import CancelledRunError, run_error
from app.agents.common.mcp import collect_ids
from app.core.config import get_settings
from app.core.errors import DomainError, ValidationError
from app.intelligence.models import AgentName, Run, RunStatus, Session
from app.orchestration.persistence import PERSISTERS
from app.orchestration.references import RunRepositories, open_session, resolve_trigger
from app.orchestration.routing import Route, Trigger, route_chat, route_trigger

logger = logging.getLogger(__name__)

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
        # ponytail: one tenant, because the MCP server is built for one company.
        # Accept other companies once the MCP is tenant-aware.
        if company_id != get_settings().default_company_id:
            raise ValidationError(f"Runs are not available for company {company_id}")
        route, trigger_context = await self._route(company_id, trigger, agent)
        session = await open_session(self.repositories, company_id, session_id)
        previous = None
        if session.last_run_id is not None:
            previous = await self.repositories.runs.get(session.last_run_id)
        context = RunContext(
            company_id=company_id,
            session_id=session.id,
            run_id=Run.new_id(),
            intent=route.intent,
            trigger_context=trigger_context,
            previous_output=previous.output if previous else None,
        )
        if trigger_context is not None:
            # The trigger record was resolved for this company, so the agent may cite it, and
            # the evidence it carries (a recommendation's), which was grounded when produced.
            context.retrieved_ids |= collect_ids(trigger_context)
        if context.previous_output is not None:
            # Follow-ups ("drop #3") may re-cite what the last answer already grounded.
            context.retrieved_ids |= collect_ids(context.previous_output)
        run = Run(
            id=context.run_id,
            session_id=session.id,
            agent=route.agent,
            intent=route.intent,
            trigger=trigger.model_dump(mode="json") if trigger else {},
            route=route.model_dump(mode="json"),
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        await self.repositories.runs.upsert(run)
        context.emit(
            "run.started", {"agent": route.agent, "intent": route.intent, "route": run.route}
        )
        clock = time.monotonic()
        try:
            outcome = await self.agents[route.agent](context, message)
            persister = PERSISTERS.get(route.agent)
            saved = await persister(self.repositories, run, outcome) if persister else {}
        except asyncio.CancelledError:
            run = self._failed(run, context, CancelledRunError("The run was cancelled"))
            await asyncio.shield(self._finish(run, context, session))
            raise
        except Exception as exc:
            error = run_error(exc)
            if not isinstance(exc, DomainError):
                logger.exception("Run %s failed", run.id, extra={"ctx": {"run_id": run.id}})
            run = self._failed(run, context, error)
        else:
            output = outcome.output.model_dump(mode="json")
            context.emit("output.final", output | saved)
            duration_ms = round((time.monotonic() - clock) * 1000)
            context.emit(
                "run.completed",
                {"status": outcome.status, "duration_ms": duration_ms, "usage": outcome.usage},
            )
            run = run.model_copy(
                update={"status": outcome.status, "output": output, "usage": outcome.usage}
            )
        return await self._finish(run, context, session)

    def _failed(self, run: Run, context: RunContext, error: DomainError) -> Run:
        detail: dict[str, object] = {"code": error.code, "message": error.message}
        context.emit("run.failed", detail)
        return run.model_copy(update={"status": RunStatus.FAILED, "error": detail})

    async def _finish(self, run: Run, context: RunContext, session: Session) -> Run:
        run = run.model_copy(
            update={
                "events": context.events,
                "tool_calls": context.tool_calls,
                "skills_loaded": context.skill_budget.loaded,
                "finished_at": datetime.now(UTC),
            }
        )
        await self.repositories.runs.upsert(run)
        if run.status is RunStatus.SUCCEEDED:
            # Follow-ups build on the last successful answer; a failure, refusal or
            # clarification must not replace it.
            await self.repositories.sessions.upsert(
                session.model_copy(update={"last_run_id": run.id})
            )
        return run

    async def _route(
        self, company_id: str, trigger: Trigger | None, agent: AgentName | None
    ) -> tuple[Route, dict[str, object] | None]:
        if trigger is not None:
            route = route_trigger(trigger)
            context = await resolve_trigger(self.repositories, trigger, company_id)
        elif agent is None:
            raise ValidationError("Chat needs an explicit agent until the router exists (Step 6)")
        else:
            route, context = route_chat(agent), None
        if route.agent not in self.agents:
            raise ValidationError(f"The {route.agent} agent is not available yet")
        return route, context
