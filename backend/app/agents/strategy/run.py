"""Run the Strategy agent once, with one grounding repair (agents-spec §6)."""

from agents import RunConfig, Usage

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.mcp import RunMCPServer
from app.agents.common.openai import model_provider
from app.agents.common.prompt import render_input
from app.agents.common.repair import OutputCheck, run_with_repair, usage_summary
from app.agents.strategy.agent import build_strategy_agent
from app.agents.strategy.output import StrategyOutput
from app.agents.strategy.validation import (
    contract_problems,
    ensure_valid,
    normalise,
    repair_message,
    unknown_ids,
)
from app.core.config import get_settings
from app.intelligence.models import RunStatus

RUN_STATUS = {
    "OK": RunStatus.SUCCEEDED,
    "INSUFFICIENT_DATA": RunStatus.SUCCEEDED,
    "NEEDS_CLARIFICATION": RunStatus.NEEDS_CLARIFICATION,
    "REFUSED": RunStatus.REFUSED,
}


def output_check(context: RunContext) -> OutputCheck[StrategyOutput]:
    def message(output: StrategyOutput) -> str | None:
        unknown = unknown_ids(output, context.retrieved_ids)
        problems = contract_problems(output, context.skill_budget.skills)
        return repair_message(unknown, problems) if unknown or problems else None

    return OutputCheck(
        repair_message=message,
        ensure_valid=lambda output: ensure_valid(
            output, context.retrieved_ids, context.skill_budget.skills
        ),
        check_label="Checking evidence",
        repair_label="Repairing citations",
    )


async def run_strategy(
    context: RunContext, message: str | None, *, mcp_url: str | None = None
) -> AgentOutcome:
    """mcp_url overrides MCP_URL, e.g. for an in-process eval server."""
    usage = Usage()
    async with (
        model_provider() as provider,
        RunMCPServer(context, mcp_url or get_settings().mcp_url) as mcp_server,
    ):
        context.emit("agent.step", {"label": "Planning and researching"})
        output = await run_with_repair(
            build_strategy_agent(context, mcp_server),
            render_input(context, message),
            context=context,
            config=RunConfig(model_provider=provider, tracing_disabled=True),
            output_type=StrategyOutput,
            check=output_check(context),
            usage=usage,
        )
    return AgentOutcome(
        status=RUN_STATUS[output.status],
        output=normalise(output),
        usage=usage_summary(usage),
    )
