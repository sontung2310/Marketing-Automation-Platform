"""Run the Execution agent once, with one contract repair (agents-spec §7)."""

from agents import RunConfig, Usage

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.mcp import RunMCPServer
from app.agents.common.openai import model_provider
from app.agents.common.prompt import render_input
from app.agents.common.repair import OutputCheck, run_with_repair, usage_summary
from app.agents.execution.agent import build_execution_agent
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

RUN_STATUS = {
    "OK": RunStatus.SUCCEEDED,
    "NEEDS_CLARIFICATION": RunStatus.NEEDS_CLARIFICATION,
    "REFUSED": RunStatus.REFUSED,
}


def output_check(
    context: RunContext, expected: DeliverableType | None
) -> OutputCheck[ExecutionOutput]:
    def message(output: ExecutionOutput) -> str | None:
        unknown = unknown_ids(output, context.retrieved_ids)
        problems = contract_problems(output, expected, context.skill_budget.skills)
        return repair_message(unknown, problems) if unknown or problems else None

    return OutputCheck(
        repair_message=message,
        ensure_valid=lambda output: ensure_valid(
            output, context.retrieved_ids, expected, context.skill_budget.skills
        ),
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
    usage = Usage()
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
            check=output_check(context, expected),
            usage=usage,
        )
    return AgentOutcome(
        status=RUN_STATUS[output.status],
        output=normalise(output),
        usage=usage_summary(usage),
    )
