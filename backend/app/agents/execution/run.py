"""Run the Execution agent once, with one contract repair (agents-spec §7)."""

from agents import RunConfig

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.mcp import RunMCPServer
from app.agents.common.openai import model_provider
from app.agents.common.prompt import render_input
from app.agents.common.repair import OutputCheck, run_with_repair, usage_summary
from app.agents.execution.agent import build_execution_agent
from app.agents.execution.guards import (
    GuardProblem,
    ensure_original,
    flag,
    guard_inputs,
    guard_problems,
)
from app.agents.execution.output import ExecutionOutput
from app.agents.execution.types import expected_type
from app.agents.execution.validation import (
    contract_problems,
    ensure_valid,
    normalise,
    repair_message,
    unknown_ids,
)
from app.core.config import get_settings
from app.intelligence.models import DeliverableType, RunStatus

QUALITY_FIX = (
    "Fix the quality problems: rewrite copied passages in your own words with a different "
    "angle, keep within the channel's length, and do not name competitors the user did not "
    "ask about. Report what you fixed in quality_check."
)

RUN_STATUS = {
    "OK": RunStatus.SUCCEEDED,
    "NEEDS_CLARIFICATION": RunStatus.NEEDS_CLARIFICATION,
    "REFUSED": RunStatus.REFUSED,
}


def problems_of(
    output: ExecutionOutput, context: RunContext, message: str | None
) -> list[GuardProblem]:
    if output.deliverable is None:
        return []
    return guard_problems(output.deliverable, guard_inputs(context, message))


def output_check(
    context: RunContext, expected: DeliverableType | None, message: str | None
) -> OutputCheck[ExecutionOutput]:
    def repair(output: ExecutionOutput) -> str | None:
        unknown = unknown_ids(output, context.retrieved_ids)
        problems = contract_problems(output, expected, context.skill_budget.skills)
        quality = problems_of(output, context, message)
        if quality:
            problems += [f"Quality: {p.message}." for p in quality]
            problems.append(QUALITY_FIX)
        return repair_message(unknown, problems) if unknown or problems else None

    def ensure(output: ExecutionOutput) -> None:
        ensure_valid(
            output,
            retrieved=context.retrieved_ids,
            expected=expected,
            loaded_skills=context.skill_budget.skills,
        )
        ensure_original(problems_of(output, context, message))

    return OutputCheck(
        repair_message=repair,
        ensure_valid=ensure,
        check_label="Checking quality",
        repair_label="Repairing the draft",
    )


def execution_input(
    context: RunContext, message: str | None, expected: DeliverableType | None
) -> str:
    text = render_input(context, message)
    if expected is None:
        return text
    return f"{text}\n\nDeliverable type: {expected} (fixed by the trigger)"


async def run_execution(
    context: RunContext, message: str | None, *, mcp_url: str | None = None
) -> AgentOutcome:
    """mcp_url overrides MCP_URL, e.g. for an in-process eval server."""
    expected = expected_type(context.intent, context.trigger_context)
    async with (
        model_provider() as provider,
        RunMCPServer(context, mcp_url or get_settings().mcp_url) as mcp_server,
    ):
        context.emit("agent.step", {"label": "Planning and researching"})
        output = await run_with_repair(
            build_execution_agent(context, mcp_server),
            execution_input(context, message, expected),
            context=context,
            config=RunConfig(model_provider=provider, tracing_disabled=True),
            output_type=ExecutionOutput,
            check=output_check(context, expected, message),
        )
    output = normalise(output)
    output = flag(output, problems_of(output, context, message))
    return AgentOutcome(
        status=RUN_STATUS[output.status],
        output=output,
        usage=usage_summary(context.usage),
    )
