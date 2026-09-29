"""Sample StrategyOutput values shared by unit and integration tests."""

from app.agents.strategy.output import Evidence, StrategyOutput, StrategyRecommendation
from app.intelligence.models import DeliverableType, NextAction, Priority


def recommendation(
    ordinal: int, evidence_id: str, kind: str = "COMPETITIVE_RESPONSE", next_action: bool = True
) -> StrategyRecommendation:
    return StrategyRecommendation.model_validate(
        {
            "ordinal": ordinal,
            "kind": kind,
            "title": f"Recommendation {ordinal}",
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
