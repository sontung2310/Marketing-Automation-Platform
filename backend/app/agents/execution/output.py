"""ExecutionOutput (agents-spec §7.2), the shape the model returns.

Kept free of length/pattern constraints so OpenAI strict structured output accepts it;
post-validation enforces the rules in code. Actions are proposals only: code builds their
payloads from the deliverable when it persists them (design D3).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.intelligence.models import ActionType, Channel, DeliverableType

ExecutionStatus = Literal["OK", "NEEDS_CLARIFICATION", "REFUSED"]
CheckStatus = Literal["PASS", "FIXED", "FLAG"]


class ExecutionDeliverable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: DeliverableType
    channel: Channel | None
    title: str
    body_markdown: str
    variants: list[str]
    word_count: int
    author_persona: str | None


class QualityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_voice: CheckStatus
    originality: CheckStatus
    factual_grounding: CheckStatus
    channel_fit: CheckStatus
    notes: list[str]


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: ActionType
    summary: str
    # Only when the user named a time or date (ISO 8601); code applies the default schedule.
    when: str | None


class ExecutionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ExecutionStatus
    message: str
    deliverable: ExecutionDeliverable | None
    quality_check: QualityCheck | None
    evidence_ids: list[str]
    skills_used: list[str]
    assumptions: list[str]
    proposed_actions: list[ActionProposal]
    clarification_options: list[str]
