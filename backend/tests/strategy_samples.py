"""Sample StrategyOutput values shared by unit and integration tests."""

from datetime import UTC, datetime, timedelta

from app.agents.strategy.output import Evidence, StrategyOutput, StrategyRecommendation
from app.intelligence.models import DeliverableType, NextAction, Priority, Run
from evals.cases import GoldenCase


def recommendation(
    ordinal: int, evidence_id: str, kind: str = "COMPETITIVE_RESPONSE", next_action: bool = True
) -> StrategyRecommendation:
    return StrategyRecommendation.model_validate(
        {
            "ordinal": ordinal,
            "kind": kind,
            "title": f"Recommendation {ordinal}",
            "insight": "Because two rivals cut prices, a value-proof angle is open to us.",
            "audience": "Founder-led B2B services firms",
            "rationale": "Evidence, then context, then method.",
            "priority": Priority.HIGH,
            "channel": None,
            "evidence": [Evidence(id=evidence_id, kind="activity", note="Why it matters")],
            "skills_used": ["pricing"],
            "next_action": NextAction(
                deliverable_type=DeliverableType.RESPONSE_BRIEF, brief="Draft a response brief"
            )
            if next_action
            else None,
        }
    )


def strategy_output(*recommendations: StrategyRecommendation) -> StrategyOutput:
    return StrategyOutput(
        status="OK",
        answer="Respond on value, not price.",
        implications=[],
        recommendations=list(recommendations),
        assumptions=[],
        data_gaps=[],
        clarification_options=[],
    )


def golden_case_data(**overrides: object) -> dict[str, object]:
    """A minimal valid golden-case line; override any top-level field."""
    base: dict[str, object] = {
        "id": "ST-T",
        "suite": "strategy",
        "category": "ST-TEST",
        "fixture": "intelligence_v2",
        "description": "test case",
        "input": {"message": "What should we post?"},
        "expect": {"status": ["OK"]},
    }
    return base | overrides


def golden_case(**overrides: object) -> GoldenCase:
    return GoldenCase.model_validate(golden_case_data(**overrides))


def sample_run(**overrides: object) -> Run:
    """A finished, successful Strategy run document; override any field."""
    started = datetime(2026, 9, 30, tzinfo=UTC)
    base: dict[str, object] = {
        "id": "run_sample",
        "session_id": "ses_sample",
        "agent": "STRATEGY",
        "intent": "CHAT",
        "status": "SUCCEEDED",
        "output": strategy_output(recommendation(1, "act_seed_001")).model_dump(mode="json"),
        "tool_calls": [{"tool": "get_company_context"}],
        "skills_loaded": ["pricing"],
        "usage": {"total_tokens": 1000},
        "started_at": started,
        "finished_at": started + timedelta(seconds=20),
    }
    return Run.model_validate(base | overrides)
