"""What differs per suite: the agent, its output type and how the checks read that output."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.agents.common.context import AgentOutcome
from app.agents.execution.config import SKILL_ALLOWLIST as EXECUTION_SKILLS
from app.agents.execution.output import ExecutionOutput
from app.agents.execution.run import run_execution
from app.agents.strategy.config import SKILL_ALLOWLIST as STRATEGY_SKILLS
from app.agents.strategy.output import StrategyOutput
from app.agents.strategy.run import run_strategy
from app.intelligence.models import AgentName
from app.orchestration.persistence import Persister, persist_execution, persist_strategy

RunAgent = Callable[..., Awaitable[AgentOutcome]]  # (context, message, *, mcp_url)


def strategy_cited(output: BaseModel) -> set[str]:
    assert isinstance(output, StrategyOutput)
    return {e.id for r in output.recommendations for e in r.evidence}


def strategy_claims(output: BaseModel) -> str:
    """Everything the agent asserts, including briefs (they become Execution's instructions)."""
    assert isinstance(output, StrategyOutput)
    parts = [output.answer, *output.implications]
    for r in output.recommendations:
        parts += [r.title, r.rationale, r.next_action.brief if r.next_action else ""]
    return " ".join(parts)


def strategy_skills(output: BaseModel) -> set[str]:
    assert isinstance(output, StrategyOutput)
    return {s for r in output.recommendations for s in r.skills_used}


def execution_cited(output: BaseModel) -> set[str]:
    assert isinstance(output, ExecutionOutput)
    return set(output.evidence_ids)


def execution_claims(output: BaseModel) -> str:
    """The message and the whole deliverable (the asset is what the user publishes)."""
    assert isinstance(output, ExecutionOutput)
    parts = [output.message]
    if (d := output.deliverable) is not None:
        parts += [d.title, d.body_markdown, *d.variants]
    return " ".join(parts)


def execution_published(output: BaseModel) -> str:
    """Only the asset: a refusal message may quote what it refuses to say."""
    assert isinstance(output, ExecutionOutput)
    d = output.deliverable
    return " ".join([d.title, d.body_markdown, *d.variants]) if d else ""


def execution_skills(output: BaseModel) -> set[str]:
    assert isinstance(output, ExecutionOutput)
    return set(output.skills_used)


@dataclass(frozen=True)
class SuiteSpec:
    agent: AgentName
    run_agent: RunAgent
    output_type: type[BaseModel]
    persist: Persister
    skill_allowlist: frozenset[str]
    cited: Callable[[BaseModel], set[str]]
    claims: Callable[[BaseModel], str]
    published: Callable[[BaseModel], str]  # what must_not_include is checked against
    skills_used: Callable[[BaseModel], set[str]]


SUITES: dict[str, SuiteSpec] = {
    "strategy": SuiteSpec(
        agent=AgentName.STRATEGY,
        run_agent=run_strategy,
        output_type=StrategyOutput,
        persist=persist_strategy,
        skill_allowlist=STRATEGY_SKILLS,
        cited=strategy_cited,
        claims=strategy_claims,
        published=strategy_claims,
        skills_used=strategy_skills,
    ),
    "execution": SuiteSpec(
        agent=AgentName.EXECUTION,
        run_agent=run_execution,
        output_type=ExecutionOutput,
        persist=persist_execution,
        skill_allowlist=EXECUTION_SKILLS,
        cited=execution_cited,
        claims=execution_claims,
        published=execution_published,
        skills_used=execution_skills,
    ),
}


def history_spec(output: dict[str, object]) -> SuiteSpec:
    """Which agent produced a session-history output (the output types are disjoint)."""
    for spec in SUITES.values():
        try:
            spec.output_type.model_validate(output)
        except ValueError:
            continue
        return spec
    raise ValueError("session_history entry is neither a StrategyOutput nor an ExecutionOutput")
