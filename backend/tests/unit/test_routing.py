"""Deterministic trigger routing (agents-spec §5.1)."""

import pytest

from app.agents.common.intents import Intent
from app.core.errors import ValidationError
from app.intelligence.models import AgentName
from app.orchestration.routing import (
    TRIGGER_ROUTES,
    RouteMethod,
    Trigger,
    TriggerAction,
    TriggerKind,
    route_chat,
    route_trigger,
)

SPEC_TABLE = {
    ("FEED_ACTION", "CREATE_SIMILAR"): ("EXECUTION", "CREATE_SIMILAR"),
    ("FEED_ACTION", "WHY_IT_MATTERS"): ("STRATEGY", "WHY_IT_MATTERS"),
    ("FEED_ACTION", "RESPONSE_PLAN"): ("STRATEGY", "STRATEGY_SYNTHESIS"),
    ("RECOMMENDATION", "DO_THIS"): ("EXECUTION", "FROM_RECOMMENDATION"),
    ("TREND", "USE_TREND"): ("STRATEGY", "STRATEGY_SYNTHESIS"),
    ("INFLUENCER", "DRAFT_OUTREACH"): ("EXECUTION", "INFLUENCER_OUTREACH"),
    ("COMPANY", "GENERATE_STRATEGY"): ("STRATEGY", "STRATEGY_SYNTHESIS"),
}


def test_registry_matches_the_spec_table() -> None:
    assert {
        (k.value, a.value): (g.value, i.value) for (k, a), (g, i) in TRIGGER_ROUTES.items()
    } == SPEC_TABLE


def test_every_kind_and_action_is_routable() -> None:
    assert {k for k, _ in TRIGGER_ROUTES} == set(TriggerKind)
    assert {a for _, a in TRIGGER_ROUTES} == set(TriggerAction)


def test_trigger_routes_deterministically() -> None:
    route = route_trigger(
        Trigger(kind=TriggerKind.FEED_ACTION, ref_id="act_1", action=TriggerAction.RESPONSE_PLAN)
    )
    assert (route.agent, route.intent, route.method) == (
        AgentName.STRATEGY,
        Intent.STRATEGY_SYNTHESIS,
        RouteMethod.DETERMINISTIC,
    )


def test_unknown_pair_is_rejected() -> None:
    with pytest.raises(ValidationError):
        route_trigger(Trigger(kind=TriggerKind.TREND, ref_id="trd_1", action=TriggerAction.DO_THIS))


def test_chat_uses_the_explicit_agent() -> None:
    route = route_chat(AgentName.STRATEGY)
    assert (route.intent, route.method) == (Intent.CHAT, RouteMethod.EXPLICIT)
