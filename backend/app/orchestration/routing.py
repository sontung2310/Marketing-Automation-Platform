"""Deterministic routing for UI triggers (agents-spec §5.1). Never calls a model."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.agents.common.intents import Intent
from app.core.errors import ValidationError
from app.intelligence.models import AgentName


class TriggerKind(StrEnum):
    FEED_ACTION = "FEED_ACTION"
    RECOMMENDATION = "RECOMMENDATION"
    TREND = "TREND"
    INFLUENCER = "INFLUENCER"


class TriggerAction(StrEnum):
    CREATE_SIMILAR = "CREATE_SIMILAR"
    WHY_IT_MATTERS = "WHY_IT_MATTERS"
    RESPONSE_PLAN = "RESPONSE_PLAN"
    DO_THIS = "DO_THIS"
    USE_TREND = "USE_TREND"
    DRAFT_OUTREACH = "DRAFT_OUTREACH"


class RouteMethod(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    EXPLICIT = "EXPLICIT"


class Trigger(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: TriggerKind
    ref_id: str = Field(min_length=1)
    action: TriggerAction


class Route(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent: AgentName
    intent: Intent
    method: RouteMethod
    reason: str
    confidence: float = Field(default=1.0, ge=0, le=1)


TRIGGER_ROUTES: dict[tuple[TriggerKind, TriggerAction], tuple[AgentName, Intent]] = {
    (TriggerKind.FEED_ACTION, TriggerAction.CREATE_SIMILAR): (
        AgentName.EXECUTION,
        Intent.CREATE_SIMILAR,
    ),
    (TriggerKind.FEED_ACTION, TriggerAction.WHY_IT_MATTERS): (
        AgentName.STRATEGY,
        Intent.WHY_IT_MATTERS,
    ),
    (TriggerKind.FEED_ACTION, TriggerAction.RESPONSE_PLAN): (
        AgentName.STRATEGY,
        Intent.RESPONSE_PLAN,
    ),
    (TriggerKind.RECOMMENDATION, TriggerAction.DO_THIS): (
        AgentName.EXECUTION,
        Intent.FROM_RECOMMENDATION,
    ),
    (TriggerKind.TREND, TriggerAction.USE_TREND): (
        AgentName.STRATEGY,
        Intent.TOPIC_RECOMMENDATION,
    ),
    (TriggerKind.INFLUENCER, TriggerAction.DRAFT_OUTREACH): (
        AgentName.EXECUTION,
        Intent.INFLUENCER_OUTREACH,
    ),
}


def route_trigger(trigger: Trigger) -> Route:
    target = TRIGGER_ROUTES.get((trigger.kind, trigger.action))
    if target is None:
        raise ValidationError(
            f"{trigger.action} is not an action for {trigger.kind} triggers",
            {"kind": trigger.kind, "action": trigger.action},
        )
    agent, intent = target
    return Route(
        agent=agent,
        intent=intent,
        method=RouteMethod.DETERMINISTIC,
        reason=f"{trigger.kind} {trigger.action} button",
    )


def route_chat(agent: AgentName) -> Route:
    """Chat needs an explicit agent until the Step 6 classifier exists."""
    return Route(
        agent=agent, intent=Intent.CHAT, method=RouteMethod.EXPLICIT, reason="agent selected"
    )
