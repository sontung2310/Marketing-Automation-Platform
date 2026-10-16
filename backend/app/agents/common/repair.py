"""Run an agent, then validate its output and repair it once (agents-spec §1)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from agents import Agent, AgentsException, RunConfig, Runner, RunResult, TResponseInputItem, Usage
from pydantic import BaseModel

from app.agents.common.context import MAX_TURNS, RunContext

OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class OutputCheck(Generic[OutputT]):
    """How one agent's output is judged: a repair prompt, or None when it is valid."""

    repair_message: Callable[[OutputT], str | None]
    # Raises the agent's domain error when the output is still invalid.
    ensure_valid: Callable[[OutputT], None]
    check_label: str
    repair_label: str


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


async def run_counting_usage(
    agent: Agent[RunContext],
    items: str | list[TResponseInputItem],
    *,
    context: RunContext,
    **kwargs: Any,
) -> RunResult:
    """`Runner.run`, adding the spend to the run even when the SDK raises mid-run."""
    try:
        result = await Runner.run(agent, items, context=context, **kwargs)
    except AgentsException as exc:
        if exc.run_data is not None:
            context.usage.add(exc.run_data.context_wrapper.usage)
        raise
    context.usage.add(result.context_wrapper.usage)
    return result


async def run_with_repair(
    agent: Agent[RunContext],
    items: str | list[TResponseInputItem],
    *,
    context: RunContext,
    config: RunConfig,
    output_type: type[OutputT],
    check: OutputCheck[OutputT],
) -> OutputT:
    result = await run_counting_usage(
        agent, items, context=context, max_turns=MAX_TURNS, run_config=config
    )
    raise_upstream(context)
    output = result.final_output_as(output_type)
    context.emit("agent.step", {"label": check.check_label})
    message = check.repair_message(output)
    if message is None:
        return output
    context.emit("agent.step", {"label": check.repair_label})
    # The repair shares the run's turn budget (agents-spec §1: max_turns=16).
    turns_left = MAX_TURNS - len(result.raw_responses)
    if turns_left < 1:  # no turn left to repair: fail hard problems, return the rest
        check.ensure_valid(output)
        return output
    repair_items = result.to_input_list()
    repair_items.append({"role": "user", "content": message})
    result = await run_counting_usage(
        agent, repair_items, context=context, max_turns=turns_left, run_config=config
    )
    raise_upstream(context)
    output = result.final_output_as(output_type)
    check.ensure_valid(output)
    return output
