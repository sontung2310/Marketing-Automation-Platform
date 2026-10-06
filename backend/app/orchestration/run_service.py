"""Prepare, run and persist one agent run (agents-spec §1).

The API prepares a run (returning its 202 at once) and executes it in the background;
events reach Mongo while the agent works, so the run stream is live.
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.errors import CancelledRunError, run_error
from app.agents.common.mcp import collect_ids
from app.core.config import get_settings
from app.core.errors import DomainError, NotFoundError, ValidationError
from app.intelligence.models import AgentName, Run, RunStatus, Session
from app.orchestration.persistence import PERSISTERS
from app.orchestration.references import RunRepositories, open_session, resolve_trigger
from app.orchestration.routing import Route, Trigger, route_chat, route_trigger

logger = logging.getLogger(__name__)

# An agent receives the run context (trigger record included) and the chat message.
AgentFn = Callable[[RunContext, str | None], Awaitable[AgentOutcome]]

EVENT_FLUSH_SECONDS = 0.5
# A run still RUNNING after this long lost its worker (a killed function, a deploy).
RUN_WALL_CLOCK = timedelta(seconds=120)


@dataclass
class RunPlan:
    """A prepared run: persisted as RUNNING, ready to execute."""

    run: Run
    context: RunContext
    session: Session
    message: str | None


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
        """Prepare and execute in one call (evals and tests)."""
        plan = await self.prepare(
            company_id, trigger=trigger, message=message, agent=agent, session_id=session_id
        )
        return await self.execute(plan)

    async def prepare(
        self,
        company_id: str,
        *,
        trigger: Trigger | None = None,
        message: str | None = None,
        agent: AgentName | None = None,
        session_id: str | None = None,
    ) -> RunPlan:
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
        route_json = route.model_dump(mode="json")
        context.emit(
            "run.started", {"agent": route.agent, "intent": route.intent, "route": route_json}
        )
        run = Run(
            id=context.run_id,
            session_id=session.id,
            agent=route.agent,
            intent=route.intent,
            trigger=trigger.model_dump(mode="json") if trigger else {},
            route=route_json,
            status=RunStatus.RUNNING,
            events=list(context.events),
            started_at=datetime.now(UTC),
        )
        await self.repositories.runs.upsert(run)
        return RunPlan(run=run, context=context, session=session, message=message)

    async def execute(self, plan: RunPlan) -> Run:
        run, context, session = plan.run, plan.context, plan.session
        writer = asyncio.create_task(self._write_events(run.id, context, len(run.events)))
        clock = time.monotonic()
        try:
            outcome = await self.agents[run.agent](context, plan.message)
            persister = PERSISTERS.get(run.agent)
            saved = (
                await persister(self.repositories, run, outcome, context.trigger_context)
                if persister
                else {}
            )
        except asyncio.CancelledError:
            run = self._failed(run, context, CancelledRunError("The run was cancelled"))
            await asyncio.shield(self._finish(run, context, session, writer))
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
                update={
                    "status": outcome.status,
                    "output": output,
                    "persisted": saved,
                    "usage": outcome.usage,
                }
            )
        return await self._finish(run, context, session, writer)

    async def load(self, run_id: str) -> Run:
        """A persisted run; one whose worker died reads as FAILED, once and for all."""
        run = await self.repositories.runs.get(run_id)
        if run is None:
            raise NotFoundError(f"{run_id} was not found", {"run_id": run_id})
        if run.status is not RunStatus.RUNNING:
            return run
        if datetime.now(UTC) - run.started_at < RUN_WALL_CLOCK:
            return run
        detail: dict[str, object] = {"code": "INTERNAL", "message": "The run was interrupted"}
        failed = {
            "run_id": run.id,
            "seq": len(run.events) + 1,
            "type": "run.failed",
            "data": detail,
            "ts": datetime.now(UTC),
        }
        run = run.model_copy(
            update={
                "status": RunStatus.FAILED,
                "error": detail,
                "events": [*run.events, failed],
                "finished_at": datetime.now(UTC),
            }
        )
        await self.repositories.runs.upsert(run)
        return run

    async def _write_events(self, run_id: str, context: RunContext, written: int) -> None:
        """Copy new events to Mongo while the agent works, so the stream is live."""
        while True:
            await asyncio.sleep(EVENT_FLUSH_SECONDS)
            if len(context.events) > written:
                written = len(context.events)
                await self.repositories.runs.set_events(run_id, context.events[:written])

    def _failed(self, run: Run, context: RunContext, error: DomainError) -> Run:
        detail: dict[str, object] = {"code": error.code, "message": error.message}
        context.emit("run.failed", detail)
        return run.model_copy(update={"status": RunStatus.FAILED, "error": detail})

    async def _finish(
        self, run: Run, context: RunContext, session: Session, writer: asyncio.Task[None]
    ) -> Run:
        writer.cancel()
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
