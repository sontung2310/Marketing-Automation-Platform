"""Build the Execution agent for one run (agents-spec §7)."""

from functools import cache
from pathlib import Path

from agents import Agent
from agents.mcp import MCPServer

from app.agents.common.context import RunContext
from app.agents.execution.config import SKILL_ALLOWLIST
from app.agents.execution.output import ExecutionOutput
from app.core.config import get_settings
from app.skills.tools import make_load_skill_tool, render_catalogue

INSTRUCTIONS_PATH = Path(__file__).with_name("instructions.md")


@cache
def instructions() -> str:
    template = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    return template.replace("{skill_catalogue}", render_catalogue(SKILL_ALLOWLIST))


def build_execution_agent(context: RunContext, mcp_server: MCPServer) -> Agent[RunContext]:
    return Agent[RunContext](
        name="Marketing Execution Agent",
        instructions=instructions(),
        model=get_settings().openai_model_agent,
        mcp_servers=[mcp_server],
        tools=[make_load_skill_tool(SKILL_ALLOWLIST, context.skill_budget)],
        output_type=ExecutionOutput,
    )
