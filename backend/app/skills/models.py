"""Typed contracts for the marketing skills catalogue and tools."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SkillErrorCode = Literal[
    "INVALID_SKILL",
    "NOT_FOUND",
    "NOT_AVAILABLE",
    "INVALID_REFERENCE",
    "LIMIT_REACHED",
    "LOAD_FAILED",
]


class SkillSummary(BaseModel):
    """The metadata exposed by ``list_skills``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SkillDocument(BaseModel):
    """A loaded skill body or one of its reference files."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    body: str
    reference: str | None = None


class SkillError(BaseModel):
    """Recoverable error returned by a skill tool."""

    model_config = ConfigDict(extra="forbid")

    code: SkillErrorCode
    message: str = Field(min_length=1)


class SkillErrorEnvelope(BaseModel):
    """The error shape returned instead of raising into an agent."""

    model_config = ConfigDict(extra="forbid")

    error: SkillError
