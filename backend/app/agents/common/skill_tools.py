"""Factories that bind the shared skill catalogue to each agent allowlist."""

from agents import FunctionTool
from app.skills.loader import SkillCatalogue, SkillLoadSession
from app.skills.registry import EXECUTION_SKILL_ALLOWLIST, STRATEGY_SKILL_ALLOWLIST
from app.skills.tools import build_skill_function_tools


def build_strategy_skill_tools(
    catalogue: SkillCatalogue,
    *,
    session: SkillLoadSession | None = None,
) -> list[FunctionTool]:
    return build_skill_function_tools(catalogue, STRATEGY_SKILL_ALLOWLIST, session=session)


def build_execution_skill_tools(
    catalogue: SkillCatalogue,
    *,
    session: SkillLoadSession | None = None,
) -> list[FunctionTool]:
    return build_skill_function_tools(catalogue, EXECUTION_SKILL_ALLOWLIST, session=session)
