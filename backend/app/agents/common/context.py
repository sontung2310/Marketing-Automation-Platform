"""Per-run state shared with agent tools. Never sent to the model (agents-spec §1)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import BaseModel

from app.agents.common.intents import Intent
from app.core.errors import DomainError
from app.intelligence.models import RunStatus
from app.skills.tools import SkillLoadBudget

MAX_MCP_CALLS_PER_RUN = 12
MAX_TURNS = 16


@dataclass
class RunContext:
    company_id: str
    session_id: str
    run_id: str
    intent: Intent
    trigger_context: dict[str, object] | None = None
    # Output of the session's previous run, for follow-ups such as "drop #3".
    previous_output: dict[str, object] | None = None
    skill_budget: SkillLoadBudget = field(default_factory=SkillLoadBudget)
    mcp_calls: int = 0
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    retrieved_ids: set[str] = field(default_factory=set)
    # Activity ID → competitor ID, for the "not all from one competitor" rule.
    activity_competitors: dict[str, str] = field(default_factory=dict)
    # Raw MCP payloads, so figures the agent quotes (e.g. summary counts) can be audited.
    tool_results: list[object] = field(default_factory=list)
    # Set when an MCP call raises; the SDK would hand it to the model as text (run.py fails).
    upstream_error: DomainError | None = None
    events: list[dict[str, object]] = field(default_factory=list)

    def emit(self, event_type: str, data: dict[str, object]) -> None:
        """Append an SSE-log event (api-contract run events) with the next `seq`."""
        self.events.append(
            {
                "run_id": self.run_id,
                "seq": len(self.events) + 1,
                "type": event_type,
                "data": data,
                "ts": datetime.now(UTC),
            }
        )


@dataclass(frozen=True)
class AgentOutcome:
    """What an agent hands back to the run service."""

    status: RunStatus
    output: BaseModel
    usage: dict[str, object] = field(default_factory=dict)
