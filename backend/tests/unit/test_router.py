"""Router decision rules (agents-spec §5.2), with no model call."""

import asyncio
from typing import get_args

import pytest
from pydantic import SecretStr

from app.agents.common.intents import Intent
from app.core.config import get_settings
from app.core.errors import UpstreamUnavailableError
from app.intelligence.models import AgentName, DeliverableType
from app.orchestration import router
from app.orchestration.references import Unresolved
from app.orchestration.router import (
    FALLBACK_OPTIONS,
    INTENT_AGENT,
    OUT_OF_SCOPE_MESSAGE,
    RouteDecision,
    RoutedIntent,
    RouterAnswer,
    classify,
    decide,
    instructions,
    route_message,
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


async def _no_reference(reference: str) -> dict[str, object] | Unresolved:
    return Unresolved(f"No recommendation #{reference.partition(':')[2]} in this session")


@pytest.mark.parametrize("confidence", [0.31, 0.92])
async def test_an_unresolvable_reference_answers_even_when_the_model_clarifies(
    confidence: float,
) -> None:
    # The real router answers a bare "#7" with CLARIFY, at any confidence (5-C, RT-REF).
    async def classifier(message: str, hint: AgentName | None) -> RouteDecision:
        return decision("CLARIFY", confidence=confidence, references=["recommendation:7"])

    _, outcome, _ = await route_message(classifier, _no_reference, "#7", None)

    assert isinstance(outcome, RouterAnswer)
    assert (outcome.status, outcome.message) == (
        "NEEDS_CLARIFICATION",
        "No recommendation #7 in this session",
    )


async def test_out_of_scope_never_resolves_references() -> None:
    async def classifier(message: str, hint: AgentName | None) -> RouteDecision:
        return decision("OUT_OF_SCOPE", references=["recommendation:7"])

    _, outcome, _ = await route_message(classifier, _no_reference, "fake reviews for #7", None)

    assert isinstance(outcome, RouterAnswer) and outcome.status == "OUT_OF_SCOPE"


async def test_a_blank_router_model_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "openai_model_router", "")

    with pytest.raises(UpstreamUnavailableError, match="OPENAI_MODEL_ROUTER"):
        await classify("hello", None)


def test_every_run_intent_the_router_can_return_has_an_agent() -> None:
    answers = {"CLARIFY", "OUT_OF_SCOPE"}
    assert set(get_args(RoutedIntent)) - answers == set(INTENT_AGENT)


async def test_a_stalled_router_model_is_a_readable_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(router, "ROUTER_TIMEOUT_SECONDS", 0.05)

    async def stalled(*args: object, **kwargs: object) -> object:
        await asyncio.sleep(5)
        raise AssertionError("not reached")

    monkeypatch.setattr(router.Runner, "run", stalled)
    monkeypatch.setattr(get_settings(), "openai_api_key", SecretStr("sk-test"))

    with pytest.raises(UpstreamUnavailableError, match="did not answer in time"):
        await classify("hello", None)
