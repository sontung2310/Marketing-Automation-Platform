"""Build the Strategy agent for one run (agents-spec §6)."""

from functools import cache
from pathlib import Path

from agents import Agent
from agents.mcp import MCPServer

from app.agents.common.context import RunContext
from app.agents.strategy.config import SKILL_ALLOWLIST
from app.agents.strategy.output import StrategyOutput
from app.core.config import get_settings
from app.skills.tools import make_load_skill_tool, render_catalogue

INSTRUCTIONS_PATH = Path(__file__).with_name("instructions.md")


@cache
def instructions() -> str:
    template = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    return template.replace("{skill_catalogue}", render_catalogue(SKILL_ALLOWLIST))


def build_strategy_agent(context: RunContext, mcp_server: MCPServer) -> Agent[RunContext]:
    return Agent[RunContext](
        name="Marketing Strategy Agent",
        instructions=instructions(),
        model=get_settings().openai_model_agent,
        mcp_servers=[mcp_server],
        tools=[make_load_skill_tool(SKILL_ALLOWLIST, context.skill_budget)],
        output_type=StrategyOutput,
    )
