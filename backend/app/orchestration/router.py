"""Chat routing (agents-spec §5.2): a small classifier decides where a message goes.

`classify` asks the router model for a `RouteDecision`; `decide` turns that decision
into a run route or a direct answer (clarify, out of scope) with no model involved, so
the rules are testable on their own.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import cache
from pathlib import Path
from typing import Literal

from agents import Agent, RunConfig, Runner
from pydantic import BaseModel

from app.agents.common.errors import run_error
from app.agents.common.intents import Intent
from app.agents.common.openai import model_provider
from app.core.config import get_settings
from app.core.errors import DomainError, UpstreamUnavailableError
from app.intelligence.models import AgentName, DeliverableType
from app.orchestration.references import Unresolved
from app.orchestration.routing import Route, RouteMethod

logger = logging.getLogger(__name__)
INSTRUCTIONS_PATH = Path(__file__).with_name("router_instructions.md")
CLARIFY_BELOW = 0.6
ROUTER_TIMEOUT_SECONDS = 15.0  # p95 target is 3 s (api-contract)
OUT_OF_SCOPE_MESSAGE = (
    "I can help with Marketing Eye's marketing: competitor moves, content ideas and drafts. "
    "That request is outside what I do."
)
FALLBACK_QUESTION = "Do you want a plan for what to do, or a draft to publish?"
FALLBACK_OPTIONS = ["Suggest what we should post next week", "Draft a LinkedIn post"]

RoutedIntent = Literal[
    "TOPIC_RECOMMENDATION",
    "RESPONSE_PLAN",
    "WHY_IT_MATTERS",
    "INFLUENCER_RECOMMENDATION",
    "TREND_ANALYSIS",
    "COMPETITOR_QUESTION",
    "FROM_RECOMMENDATION",
    "FREEFORM_DELIVERABLE",
    "INFLUENCER_OUTREACH",
    "REVISE_DELIVERABLE",
    "CLARIFY",
    "OUT_OF_SCOPE",
]


class RouteDecision(BaseModel):
    """The router model's structured output (agents-spec §5.2)."""

    agent: Literal["STRATEGY", "EXECUTION", "NONE"]
    intent: RoutedIntent
    deliverable_type: DeliverableType | None
    references: list[str]  # "recommendation:N" or "deliverable:last"
    confidence: float
    reason: str
    clarification_question: str | None
    clarification_options: list[str]


class RouterAnswer(BaseModel):
    """A reply without an agent run (api-contract `POST /runs`, 200)."""

    status: Literal["NEEDS_CLARIFICATION", "OUT_OF_SCOPE"]
    message: str
    clarification_options: list[str]
    route: Route


# Which agent serves each run intent; CLARIFY and OUT_OF_SCOPE run no agent.
INTENT_AGENT: dict[Intent, AgentName] = {
    Intent.TOPIC_RECOMMENDATION: AgentName.STRATEGY,
    Intent.RESPONSE_PLAN: AgentName.STRATEGY,
    Intent.WHY_IT_MATTERS: AgentName.STRATEGY,
    Intent.INFLUENCER_RECOMMENDATION: AgentName.STRATEGY,
    Intent.TREND_ANALYSIS: AgentName.STRATEGY,
    Intent.COMPETITOR_QUESTION: AgentName.STRATEGY,
    Intent.FROM_RECOMMENDATION: AgentName.EXECUTION,
    Intent.FREEFORM_DELIVERABLE: AgentName.EXECUTION,
    Intent.INFLUENCER_OUTREACH: AgentName.EXECUTION,
    Intent.REVISE_DELIVERABLE: AgentName.EXECUTION,
}
# What a hinted agent does with a message the classifier gave to the other one.
HINT_DEFAULT_INTENT: dict[AgentName, Intent] = {
    AgentName.STRATEGY: Intent.COMPETITOR_QUESTION,
    AgentName.EXECUTION: Intent.FREEFORM_DELIVERABLE,
}

Classifier = Callable[[str, AgentName | None], Awaitable[RouteDecision]]


def _answer_route(decision: RouteDecision, hint: AgentName | None) -> Route:
    return Route(
        agent=hint or AgentName.STRATEGY,  # unused for answers; Route needs an agent
        intent=Intent.CHAT,
        method=RouteMethod.EXPLICIT if hint else RouteMethod.CLASSIFIER,
        reason=decision.reason,
        confidence=min(max(decision.confidence, 0.0), 1.0),
    )


def decide(decision: RouteDecision, hint: AgentName | None) -> Route | RouterAnswer:
    """The run route for a decision, or the direct answer when no agent should run."""
    answered = _answer_route(decision, hint)
    method, confidence = answered.method, answered.confidence
    if decision.intent == "OUT_OF_SCOPE":  # even with a hint: never run a disallowed ask
        return RouterAnswer(
            status="OUT_OF_SCOPE",
            message=OUT_OF_SCOPE_MESSAGE,
            clarification_options=[],
            route=answered,
        )
    run_intent = next((i for i in INTENT_AGENT if i == decision.intent), None)
    agent = INTENT_AGENT[run_intent] if run_intent else None
    unsure = agent is None or confidence < CLARIFY_BELOW
    if hint is None and unsure:
        options = decision.clarification_options[:3]
        return RouterAnswer(
            status="NEEDS_CLARIFICATION",
            message=decision.clarification_question or FALLBACK_QUESTION,
            clarification_options=options if len(options) >= 2 else FALLBACK_OPTIONS,
            route=answered,
        )
    if hint is not None and agent is not hint:
        # The marketer chose the agent; it decides the scope.
        intent, agent = HINT_DEFAULT_INTENT[hint], hint
    else:
        assert run_intent is not None and agent is not None  # unsure answers returned above
        intent = run_intent
    return Route(
        agent=agent,
        intent=intent,
        method=method,
        reason=decision.reason,
        confidence=confidence,
        deliverable_type=decision.deliverable_type,
    )


ReferenceLookup = Callable[[str], Awaitable[dict[str, object] | Unresolved]]


async def route_message(
    classifier: Classifier, lookup: ReferenceLookup, message: str, hint: AgentName | None
) -> tuple[RouteDecision, Route | RouterAnswer, dict[str, object] | None]:
    """Classify a chat message and resolve what it points at in the session.

    A reference that resolves to nothing answers "No recommendation #N in this session"
    whatever else the model decided, so the marketer learns why nothing ran.
    """
    decision = await classifier(message, hint)
    context = None
    if decision.intent != "OUT_OF_SCOPE":
        for reference in decision.references[:1]:
            resolved = await lookup(reference)
            if isinstance(resolved, Unresolved):
                unresolved = RouterAnswer(
                    status="NEEDS_CLARIFICATION",
                    message=resolved.message,
                    clarification_options=[],
                    route=_answer_route(decision, hint),
                )
                return decision, unresolved, None
            context = resolved
    return decision, decide(decision, hint), context


@cache
def _instructions_template() -> str:
    return INSTRUCTIONS_PATH.read_text(encoding="utf-8")


def instructions(hint: AgentName | None) -> str:
    note = (
        f"The marketer chose the {hint} agent. Pick the intent within {hint}; "
        "still use OUT_OF_SCOPE for a request no marketing agent may serve."
        if hint
        else ""
    )
    return _instructions_template().replace("{hint}", note).strip()


async def classify(message: str, hint: AgentName | None) -> RouteDecision:
    """Ask the router model (OPENAI_MODEL_ROUTER) for a structured decision."""
    model = get_settings().openai_model_router
    if not model:  # a blank value must not fall back to the SDK's larger default model
        raise UpstreamUnavailableError("OPENAI_MODEL_ROUTER is not configured")
    agent = Agent(
        name="Request Router",
        instructions=instructions(hint),
        model=model,
        output_type=RouteDecision,
    )
    try:
        async with model_provider() as provider:
            # The 202 waits for this call, so it is bounded well under the function limit.
            async with asyncio.timeout(ROUTER_TIMEOUT_SECONDS):
                result = await Runner.run(
                    agent,
                    message,
                    max_turns=1,  # one structured answer, no tools
                    run_config=RunConfig(model_provider=provider, tracing_disabled=True),
                )
    except TimeoutError as exc:
        raise UpstreamUnavailableError("The router model did not answer in time") from exc
    except DomainError:
        raise
    except Exception as exc:
        logger.exception("The router failed")
        raise run_error(exc) from exc
    return result.final_output_as(RouteDecision)
