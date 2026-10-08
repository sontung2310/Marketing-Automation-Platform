"""StrategyOutput (agents-spec §6.2).

Kept free of length/pattern constraints so OpenAI strict structured output accepts it;
post-validation enforces the rules in code.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.intelligence.models import Channel, NextAction, Priority

RecommendationKind = Literal[
    "CONTENT_TOPIC", "COMPETITIVE_RESPONSE", "INFLUENCER_PARTNERSHIP", "CHANNEL_PLAY", "MONITOR"
]
StrategyStatus = Literal["OK", "NEEDS_CLARIFICATION", "REFUSED", "INSUFFICIENT_DATA"]


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["activity", "trend", "influencer", "company"]
    note: str


class StrategyRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal: int
    kind: RecommendationKind
    title: str
    insight: str  # one sentence: converging signals → white space → why we can own it
    audience: str  # the specific segment; MONITOR may leave both empty
    rationale: str
    priority: Priority
    channel: Channel | None
    evidence: list[Evidence]
    skills_used: list[str]
    next_action: NextAction | None


class StrategyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StrategyStatus
    answer: str
    implications: list[str]
    recommendations: list[StrategyRecommendation]
    assumptions: list[str]
    data_gaps: list[str]
    clarification_options: list[str]
