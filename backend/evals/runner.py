"""Run golden cases against the real agent, MCP and a throwaway fixture database."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any

from pydantic import BaseModel

from app.agents.common.context import AgentOutcome, RunContext
from app.core.config import get_settings
from app.intelligence.models import Run, RunStatus, Session
from app.orchestration.references import RunRepositories
from app.orchestration.routing import Trigger
from app.orchestration.run_service import AgentFn, RunService
from evals.cases import HISTORY_REF, GoldenCase
from evals.fixture import FixtureBundle, install_fixture, shifted_to
from evals.runtime import serve_mcp, throwaway_database
from evals.suites import SUITES, history_spec

AgentFactory = Callable[[str], AgentFn]  # MCP URL -> agent function


class RunRecord(BaseModel):
    case_id: str
    repeat: int
    run: Run | None  # None: the case could not start a run
    retrieved_ids: list[str]  # IDs the run's tools returned (for evidence_grounded)
    tool_results: list[Any] = []  # raw tool payloads (for no_invented_numbers)
    error: str | None = None  # the case could not start a run


async def seed_history(
    repositories: RunRepositories, company_id: str, case: GoldenCase
) -> tuple[str, list[str]]:
    """A session whose latest successful run answered with the case's last history output
    (Strategy or Execution), saved as that agent saves it, so follow-ups can resolve and
    re-cite it. Returns the session and any recommendation IDs, in ordinal order."""
    raw = case.input.session_history[-1]
    spec = history_spec(raw)
    output = spec.output_type.model_validate(raw)
    now = datetime.now(UTC)
    session = Session(id=Session.new_id(), company_id=company_id, created_at=now)
    run = Run(
        id=Run.new_id(),
        session_id=session.id,
        agent=spec.agent,
        intent="CHAT",
        status=RunStatus.SUCCEEDED,
        output=output.model_dump(mode="json"),
        started_at=now,
        finished_at=now,
    )
    # The session first, as a real run saves it: persisting finds the company through it.
    await repositories.sessions.upsert(session)
    await repositories.runs.upsert(run)
    saved = await spec.persist(repositories, run, AgentOutcome(RunStatus.SUCCEEDED, output), None)
    await repositories.sessions.upsert(session.model_copy(update={"last_run_id": run.id}))
    ids = saved.get("recommendation_ids", [])
    return session.id, [str(i) for i in ids] if isinstance(ids, list) else []


def resolve_history_ref(trigger: Trigger | None, recommendation_ids: list[str]) -> Trigger | None:
    """Point a "history:N" trigger at recommendation N of the seeded session."""
    if trigger is None or not (match := HISTORY_REF.match(trigger.ref_id)):
        return trigger
    ordinal = int(match.group(1))
    if not 1 <= ordinal <= len(recommendation_ids):
        raise ValueError(f"history has no recommendation #{ordinal}")
    return trigger.model_copy(update={"ref_id": recommendation_ids[ordinal - 1]})


async def run_suite(
    suite: str,
    cases: list[GoldenCase],
    fixture: FixtureBundle,
    *,
    now: datetime,
    repeats: int,
    concurrency: int = 4,
    agent_factory: AgentFactory | None = None,
) -> list[RunRecord]:
    company_id = get_settings().default_company_id
    spec = SUITES[suite]
    agent_name = spec.agent
    retrieved: dict[str, list[str]] = {}
    results: dict[str, list[Any]] = {}
    async with throwaway_database("marketing_automation_eval") as database:
        # The fixture is shifted to `now` and the MCP clock frozen there, so recency windows
        # (30-day lookback, 21-day staleness) cannot drift during a long suite.
        await install_fixture(database, shifted_to(fixture, now))
        repositories = RunRepositories.for_database(database)
        async with serve_mcp(database, company_id, now=lambda: now) as mcp_url:
            agent = (
                agent_factory(mcp_url)
                if agent_factory
                else partial(spec.run_agent, mcp_url=mcp_url)
            )

            async def capturing(context: RunContext, message: str | None) -> AgentOutcome:
                try:
                    return await agent(context, message)
                finally:
                    retrieved[context.run_id] = sorted(context.retrieved_ids)
                    results[context.run_id] = context.tool_results

            # Suites run more cases than the demo's daily cap allows in one database.
            service = RunService(repositories, {agent_name: capturing}, daily_cap=False)
            gate = asyncio.Semaphore(concurrency)

            async def one(case: GoldenCase, repeat: int) -> RunRecord:
                async with gate:
                    # One broken case must not lose the other runs (and their OpenAI spend).
                    try:
                        session_id: str | None = None
                        recommendation_ids: list[str] = []
                        if case.input.session_history:
                            session_id, recommendation_ids = await seed_history(
                                repositories, company_id, case
                            )
                        run = await service.start(
                            company_id,
                            trigger=resolve_history_ref(case.input.trigger, recommendation_ids),
                            message=case.input.message,
                            agent=agent_name,
                            session_id=session_id,
                        )
                    except Exception as exc:
                        return RunRecord(
                            case_id=case.id,
                            repeat=repeat,
                            run=None,
                            retrieved_ids=[],
                            error=str(exc),
                        )
                    return RunRecord(
                        case_id=case.id,
                        repeat=repeat,
                        run=run,
                        retrieved_ids=retrieved.get(run.id, []),
                        tool_results=results.get(run.id, []),
                    )

            return await asyncio.gather(
                *(one(case, repeat) for case in cases for repeat in range(1, repeats + 1))
            )
