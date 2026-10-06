"""Router decision rules (agents-spec §5.2), with no model call."""

import pytest

from app.agents.common.intents import Intent
from app.intelligence.models import AgentName, DeliverableType
from app.orchestration.router import (
    FALLBACK_OPTIONS,
    OUT_OF_SCOPE_MESSAGE,
    RouteDecision,
    RouterAnswer,
    decide,
    instructions,
)
from app.orchestration.routing import Route, RouteMethod


def decision(intent: str, *, confidence: float = 0.9, **extra: object) -> RouteDecision:
    fields: dict[str, object] = {
        "agent": "NONE",
        "intent": intent,
        "deliverable_type": None,
        "references": [],
        "confidence": confidence,
        "reason": "asked to draft a post",
        "clarification_question": None,
        "clarification_options": [],
    } | extra
    return RouteDecision.model_validate(fields)


@pytest.mark.parametrize(
    ("intent", "agent"),
    [("TOPIC_RECOMMENDATION", AgentName.STRATEGY), ("REVISE_DELIVERABLE", AgentName.EXECUTION)],
)
def test_a_confident_decision_routes_by_intent(intent: str, agent: AgentName) -> None:
    route = decide(decision(intent, deliverable_type=DeliverableType.LINKEDIN_POST), None)
    assert isinstance(route, Route)
    assert (route.agent, route.intent, route.method) == (agent, Intent(intent), "CLASSIFIER")
    assert route.deliverable_type is DeliverableType.LINKEDIN_POST


def test_low_confidence_clarifies_with_the_models_options() -> None:
    options = ["Plan a LinkedIn content calendar", "Draft a LinkedIn post"]
    answer = decide(
        decision(
            "FREEFORM_DELIVERABLE",
            confidence=0.4,
            clarification_question="What should I do on LinkedIn?",
            clarification_options=options,
        ),
        None,
    )
    assert isinstance(answer, RouterAnswer)
    assert (answer.status, answer.message, answer.clarification_options) == (
        "NEEDS_CLARIFICATION",
        "What should I do on LinkedIn?",
        options,
    )


def test_clarify_without_usable_options_falls_back() -> None:
    answer = decide(decision("CLARIFY", clarification_options=["only one"]), None)
    assert isinstance(answer, RouterAnswer)
    assert answer.clarification_options == FALLBACK_OPTIONS


@pytest.mark.parametrize("hint", [None, AgentName.EXECUTION])
def test_out_of_scope_is_answered_even_with_a_hint(hint: AgentName | None) -> None:
    answer = decide(decision("OUT_OF_SCOPE"), hint)
    assert isinstance(answer, RouterAnswer)
    assert (answer.status, answer.message) == ("OUT_OF_SCOPE", OUT_OF_SCOPE_MESSAGE)


def test_a_hint_keeps_its_agent_and_skips_clarification() -> None:
    mismatch = decide(decision("FREEFORM_DELIVERABLE", confidence=0.3), AgentName.STRATEGY)
    assert isinstance(mismatch, Route)
    assert (mismatch.agent, mismatch.intent, mismatch.method) == (
        AgentName.STRATEGY,
        Intent.COMPETITOR_QUESTION,
        RouteMethod.EXPLICIT,
    )
    match = decide(decision("TOPIC_RECOMMENDATION"), AgentName.STRATEGY)
    assert isinstance(match, Route) and match.intent is Intent.TOPIC_RECOMMENDATION


def test_instructions_name_the_hint_only_when_given() -> None:
    assert "{hint}" not in instructions(None)
    assert "chose the STRATEGY agent" in instructions(AgentName.STRATEGY)
