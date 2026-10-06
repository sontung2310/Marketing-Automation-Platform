"""Chat routing (agents-spec §5.2): a small classifier decides where a message goes.

`classify` asks the router model for a `RouteDecision`; `decide` turns that decision
into a run route or a direct answer (clarify, out of scope) with no model involved, so
the rules are testable on their own.
"""

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
from app.core.errors import DomainError
from app.intelligence.models import AgentName, DeliverableType
from app.orchestration.routing import Route, RouteMethod

INSTRUCTIONS_PATH = Path(__file__).with_name("router_instructions.md")
CLARIFY_BELOW = 0.6
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
INTENT_AGENT: dict[str, AgentName] = {
    "TOPIC_RECOMMENDATION": AgentName.STRATEGY,
    "RESPONSE_PLAN": AgentName.STRATEGY,
    "WHY_IT_MATTERS": AgentName.STRATEGY,
    "INFLUENCER_RECOMMENDATION": AgentName.STRATEGY,
    "TREND_ANALYSIS": AgentName.STRATEGY,
    "COMPETITOR_QUESTION": AgentName.STRATEGY,
    "FROM_RECOMMENDATION": AgentName.EXECUTION,
    "FREEFORM_DELIVERABLE": AgentName.EXECUTION,
    "INFLUENCER_OUTREACH": AgentName.EXECUTION,
    "REVISE_DELIVERABLE": AgentName.EXECUTION,
}
# What a hinted agent does with a message the classifier gave to the other one.
HINT_DEFAULT_INTENT: dict[AgentName, Intent] = {
    AgentName.STRATEGY: Intent.COMPETITOR_QUESTION,
    AgentName.EXECUTION: Intent.FREEFORM_DELIVERABLE,
}

Classifier = Callable[[str, AgentName | None], Awaitable[RouteDecision]]


def decide(decision: RouteDecision, hint: AgentName | None) -> Route | RouterAnswer:
    """The run route for a decision, or the direct answer when no agent should run."""
    method = RouteMethod.EXPLICIT if hint else RouteMethod.CLASSIFIER
    confidence = min(max(decision.confidence, 0.0), 1.0)
    answered = Route(
        agent=hint or AgentName.STRATEGY,  # unused for answers; Route needs an agent
        intent=Intent.CHAT,
        method=method,
        reason=decision.reason,
        confidence=confidence,
    )
    if decision.intent == "OUT_OF_SCOPE":  # even with a hint: never run a disallowed ask
        return RouterAnswer(
            status="OUT_OF_SCOPE",
            message=OUT_OF_SCOPE_MESSAGE,
            clarification_options=[],
            route=answered,
        )
    agent = INTENT_AGENT.get(decision.intent)
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
        intent = HINT_DEFAULT_INTENT[hint]  # the marketer chose the agent; it decides scope
    else:
        intent = Intent(decision.intent)
    return Route(
        agent=hint or INTENT_AGENT[decision.intent],
        intent=intent,
        method=method,
        reason=decision.reason,
        confidence=confidence,
        deliverable_type=decision.deliverable_type,
    )


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
    agent = Agent(
        name="Request Router",
        instructions=instructions(hint),
        model=get_settings().openai_model_router,
        output_type=RouteDecision,
    )
    try:
        async with model_provider() as provider:
            result = await Runner.run(
                agent,
                message,
                run_config=RunConfig(model_provider=provider, tracing_disabled=True),
            )
    except DomainError:
        raise
    except Exception as exc:
        raise run_error(exc) from exc
    return result.final_output_as(RouteDecision)
