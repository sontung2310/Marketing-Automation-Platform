"""Run golden cases against the real agent, MCP and a throwaway fixture database."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from uuid import uuid4

from pydantic import BaseModel

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.strategy.run import run_strategy
from app.core import db
from app.core.config import get_settings
from app.intelligence.models import AgentName, Run, RunStatus, Session
from app.orchestration.references import RunRepositories
from app.orchestration.run_service import AgentFn, RunService
from evals.cases import GoldenCase
from evals.fixture import FixtureBundle, install_fixture
from evals.runtime import serve_mcp

# Which agent serves each suite while the chat classifier (Step 6) does not exist.
SUITE_AGENT = {"strategy": AgentName.STRATEGY}
AgentFactory = Callable[[str], AgentFn]  # MCP URL -> agent function


def real_agents(mcp_url: str) -> AgentFn:
    return partial(run_strategy, mcp_url=mcp_url)


class RunRecord(BaseModel):
    case_id: str
    repeat: int
    run: dict[str, object] | None  # the persisted Run, JSON-ready
    retrieved_ids: list[str]  # IDs the run's tools returned (for evidence_grounded)
    error: str | None = None  # the case could not start a run


async def seed_history(repositories: RunRepositories, company_id: str, case: GoldenCase) -> str:
    """A session whose latest successful run answered with the case's last history output."""
    now = datetime.now(UTC)
    session = Session(id=Session.new_id(), company_id=company_id, created_at=now)
    run = Run(
        id=Run.new_id(),
        session_id=session.id,
        agent=AgentName.STRATEGY,
        intent="CHAT",
        status=RunStatus.SUCCEEDED,
        output=case.input.session_history[-1],
        started_at=now,
        finished_at=now,
    )
    await repositories.runs.upsert(run)
    await repositories.sessions.upsert(session.model_copy(update={"last_run_id": run.id}))
    return session.id


async def run_suite(
    suite: str,
    cases: list[GoldenCase],
    fixture: FixtureBundle,
    *,
    repeats: int,
    concurrency: int = 4,
    agent_factory: AgentFactory = real_agents,
) -> list[RunRecord]:
    company_id = get_settings().default_company_id
    agent_name = SUITE_AGENT[suite]
    name = f"marketing_automation_eval_{uuid4().hex[:12]}"
    database = db.get_client()[name]
    retrieved: dict[str, list[str]] = {}
    try:
        await install_fixture(database, fixture)
        repositories = RunRepositories.for_database(database)
        async with serve_mcp(database, company_id) as mcp_url:
            agent = agent_factory(mcp_url)

            async def capturing(context: RunContext, message: str | None) -> AgentOutcome:
                try:
                    return await agent(context, message)
                finally:
                    retrieved[context.run_id] = sorted(context.retrieved_ids)

            service = RunService(repositories, {agent_name: capturing})
            gate = asyncio.Semaphore(concurrency)

            async def one(case: GoldenCase, repeat: int) -> RunRecord:
                async with gate:
                    session_id = None
                    if case.input.session_history:
                        session_id = await seed_history(repositories, company_id, case)
                    try:
                        run = await service.start(
                            company_id,
                            trigger=case.input.trigger,
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
                        run=run.model_dump(mode="json"),
                        retrieved_ids=retrieved.get(run.id, []),
                    )

            return await asyncio.gather(
                *(one(case, repeat) for case in cases for repeat in range(1, repeats + 1))
            )
    finally:
        await db.get_client().drop_database(name)
