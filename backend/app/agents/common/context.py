"""Per-run state shared with agent tools. Never sent to the model (agents-spec §1)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.agents.common.intents import Intent
from app.skills.tools import SkillLoadBudget

MAX_MCP_CALLS_PER_RUN = 12


@dataclass
class RunContext:
    company_id: str
    session_id: str
    run_id: str
    intent: Intent
    trigger_context: dict[str, object] | None = None
    skill_budget: SkillLoadBudget = field(default_factory=SkillLoadBudget)
    mcp_calls: int = 0
    tool_calls: list[dict[str, object]] = field(default_factory=list)
    retrieved_ids: set[str] = field(default_factory=set)
    events: list[dict[str, object]] = field(default_factory=list)

    def emit(self, event_type: str, data: dict[str, object]) -> None:
        """Append an SSE-log event (api-contract run events) with the next `seq`."""
        self.events.append(
            {
                "seq": len(self.events) + 1,
                "type": event_type,
                "data": data,
                "at": datetime.now(UTC),
            }
        )
