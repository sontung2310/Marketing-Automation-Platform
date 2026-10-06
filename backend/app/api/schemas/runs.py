"""POST /api/runs body (api-contract "Agent runs")."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.orchestration.routing import Trigger


class AgentHint(StrEnum):
    AUTO = "AUTO"
    STRATEGY = "STRATEGY"
    EXECUTION = "EXECUTION"


class RunRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, min_length=1, max_length=4000)
    agent_hint: AgentHint = AgentHint.AUTO
    trigger: Trigger | None = None
