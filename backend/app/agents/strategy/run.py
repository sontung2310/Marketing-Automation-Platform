"""Run the Strategy agent once, with one grounding repair (agents-spec §6)."""

from agents import RunConfig, Runner, TResponseInputItem, Usage

from app.agents.common.context import AgentOutcome, RunContext
from app.agents.common.mcp import RunMCPServer
from app.agents.common.openai import model_provider
from app.agents.common.prompt import render_input
from app.agents.strategy.agent import MAX_TURNS, build_strategy_agent
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


def usage_summary(usage: Usage) -> dict[str, object]:
    return {
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
    }


def raise_upstream(context: RunContext) -> None:
    """An MCP failure the SDK turned into tool text still fails the run (nothing swallowed)."""
    if context.upstream_error is not None:
        raise context.upstream_error


async def run_strategy(
    context: RunContext, message: str | None, *, mcp_url: str | None = None
) -> AgentOutcome:
    """mcp_url overrides MCP_URL, e.g. for an in-process eval server."""
    usage = Usage()
    async with (
        model_provider() as provider,
        RunMCPServer(context, mcp_url or get_settings().mcp_url) as mcp_server,
    ):
        config = RunConfig(model_provider=provider, tracing_disabled=True)
        agent = build_strategy_agent(context, mcp_server)
        context.emit("agent.step", {"label": "Planning and researching"})
        items: str | list[TResponseInputItem] = render_input(context, message)
        result = await Runner.run(
            agent, items, context=context, max_turns=MAX_TURNS, run_config=config
        )
        usage.add(result.context_wrapper.usage)
        raise_upstream(context)
        output = result.final_output_as(StrategyOutput)
        context.emit("agent.step", {"label": "Checking evidence"})
        unknown = unknown_ids(output, context.retrieved_ids)
        problems = contract_problems(output, context.skill_budget.skills)
        if unknown or problems:
            context.emit("agent.step", {"label": "Repairing citations"})
            items = result.to_input_list()
            items.append({"role": "user", "content": repair_message(unknown, problems)})
            # The repair shares the run's turn budget (agents-spec §1: max_turns=16).
            turns_left = MAX_TURNS - len(result.raw_responses)
            if turns_left < 1:
                ensure_valid(output, context.retrieved_ids, context.skill_budget.skills)
            result = await Runner.run(
                agent, items, context=context, max_turns=turns_left, run_config=config
            )
            usage.add(result.context_wrapper.usage)
            raise_upstream(context)
            output = result.final_output_as(StrategyOutput)
            ensure_valid(output, context.retrieved_ids, context.skill_budget.skills)
    return AgentOutcome(
        status=RUN_STATUS[output.status],
        output=normalise(output),
        usage=usage_summary(usage),
    )
