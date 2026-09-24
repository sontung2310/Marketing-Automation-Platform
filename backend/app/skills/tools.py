"""Typed skill tools shared by the Strategy and Execution agents."""

from __future__ import annotations

from dataclasses import dataclass

from agents import FunctionTool, function_tool
from app.skills.loader import SkillCatalogue, SkillLoaderError, SkillLoadSession
from app.skills.models import (
    SkillDocument,
    SkillError,
    SkillErrorCode,
    SkillErrorEnvelope,
    SkillSummary,
)


@dataclass
class SkillToolset:
    """An allowlisted pair of tools bound to one run's load budget."""

    catalogue: SkillCatalogue
    allowed_names: frozenset[str]
    session: SkillLoadSession

    def list_skills(self) -> list[SkillSummary]:
        """Return only summaries for the current agent's allowlist."""

        return self.catalogue.summaries(self.allowed_names)

    def load_skill(
        self,
        name: str,
        reference: str | None = None,
    ) -> SkillDocument | SkillErrorEnvelope:
        """Load an allowlisted skill or return a recoverable error envelope."""

        if not self.session.consume():
            return _error("LIMIT_REACHED", "The per-run skill load limit of 3 has been reached")
        if not isinstance(name, str) or name not in self.allowed_names:
            return _error("NOT_AVAILABLE", f"Skill '{name}' is not available to this agent")
        try:
            return self.catalogue.load(name, reference)
        except SkillLoaderError as exc:
            return _error(exc.code, exc.message)
        except Exception as exc:
            return _error("LOAD_FAILED", f"Could not load skill '{name}': {exc}")


def build_skill_toolset(
    catalogue: SkillCatalogue,
    allowed_names: frozenset[str],
    *,
    session: SkillLoadSession | None = None,
) -> SkillToolset:
    """Bind a validated catalogue and allowlist to a per-run toolset."""

    missing = sorted(allowed_names - set(catalogue.names))
    if missing:
        raise ValueError(f"Allowlist names are not in the catalogue: {missing}")
    return SkillToolset(catalogue, allowed_names, session or SkillLoadSession())


def build_skill_function_tools(
    catalogue: SkillCatalogue,
    allowed_names: frozenset[str],
    *,
    session: SkillLoadSession | None = None,
) -> list[FunctionTool]:
    """Build Agents SDK function tools bound to one catalogue and run."""

    toolset = build_skill_toolset(catalogue, allowed_names, session=session)

    @function_tool
    def list_skills() -> list[SkillSummary]:
        """List the marketing skills available to this agent."""

        return toolset.list_skills()

    @function_tool
    def load_skill(name: str, reference: str | None = None) -> SkillDocument | SkillErrorEnvelope:
        """Load one allowlisted skill or a reference file from its references directory."""

        return toolset.load_skill(name, reference)

    return [list_skills, load_skill]


def _error(code: SkillErrorCode, message: str) -> SkillErrorEnvelope:
    return SkillErrorEnvelope(error=SkillError(code=code, message=message))
