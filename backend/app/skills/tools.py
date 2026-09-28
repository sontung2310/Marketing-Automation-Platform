"""The `load_skill` agent tool: allowlisted, budgeted, and never raising into the agent."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from agents import FunctionTool, function_tool
from app.core.config import get_settings
from app.skills.loader import (
    PRODUCT_CONTEXT_NOTE,
    InvalidReferenceError,
    load_catalogue,
    read_reference,
)

MAX_LOADS_PER_RUN = 3


class SkillErrorCode(StrEnum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INVALID_REFERENCE = "INVALID_REFERENCE"
    LIMIT_REACHED = "LIMIT_REACHED"


class SkillContent(BaseModel):
    ok: Literal[True] = True
    name: str
    description: str
    reference: str | None
    content: str
    truncated: bool
    references: list[str]


class SkillError(BaseModel):
    ok: Literal[False] = False
    code: SkillErrorCode
    message: str


@dataclass
class SkillLoadBudget:
    """Successful loads in one agent run; create one per run."""

    limit: int = MAX_LOADS_PER_RUN
    used: int = 0


def render_catalogue(allowlist: frozenset[str]) -> str:
    """The agent's skills as instruction text, one `- name: description` line each."""
    catalogue = load_catalogue()
    return "\n".join(f"- {n}: {catalogue[n].meta.description}" for n in sorted(allowlist))


def load_skill(
    name: str, reference: str | None, *, allowlist: frozenset[str], budget: SkillLoadBudget
) -> SkillContent | SkillError:
    if name not in allowlist:
        return SkillError(
            code=SkillErrorCode.NOT_AVAILABLE,
            message=f"Skill {name!r} is not available to this agent. Use: {sorted(allowlist)}.",
        )
    if budget.used >= budget.limit:
        return SkillError(
            code=SkillErrorCode.LIMIT_REACHED,
            message=f"All {budget.limit} skill loads are used. Finish with what you have.",
        )
    skill = load_catalogue()[name]
    try:
        text = read_reference(skill, reference) if reference else skill.body
    except InvalidReferenceError as exc:
        return SkillError(code=SkillErrorCode.INVALID_REFERENCE, message=str(exc))
    budget.used += 1
    max_chars = get_settings().skill_max_chars
    truncated = len(text) > max_chars
    if truncated:
        text = f"{text[:max_chars]}\n\n[Truncated at {max_chars} characters.]"
    return SkillContent(
        name=name,
        description=skill.meta.description,
        reference=reference,
        content=f"{text}\n\n{PRODUCT_CONTEXT_NOTE}",
        truncated=truncated,
        references=skill.references,
    )


def make_load_skill_tool(allowlist: frozenset[str], budget: SkillLoadBudget) -> FunctionTool:
    """Build the per-run `load_skill` tool bound to one agent's allowlist and budget."""

    def load_skill_tool(name: str, reference: str | None = None) -> str:
        """Load a marketing skill's instructions, or one of its reference files.

        Args:
            name: The skill name from your skills catalogue.
            reference: Optional reference path such as "references/templates.md".
        """
        return load_skill(name, reference, allowlist=allowlist, budget=budget).model_dump_json()

    return function_tool(load_skill_tool, name_override="load_skill")
