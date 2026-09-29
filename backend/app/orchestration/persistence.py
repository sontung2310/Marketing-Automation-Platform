"""Persist each agent's structured output; the returned IDs join the output.final event."""

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.agents.strategy.output import StrategyOutput
from app.intelligence.models import AgentName, Recommendation, RecommendationStatus, Run
from app.orchestration.references import RunRepositories

Persister = Callable[[RunRepositories, Run, BaseModel], Awaitable[dict[str, object]]]


async def persist_strategy(
    repositories: RunRepositories, run: Run, output: BaseModel
) -> dict[str, object]:
    if not isinstance(output, StrategyOutput):
        raise TypeError(f"Strategy runs return StrategyOutput, got {type(output).__name__}")
    recommendations = [
        Recommendation.model_validate(
            rec.model_dump()
            | {
                "id": Recommendation.new_id(),
                "run_id": run.id,
                "session_id": run.session_id,
                "status": RecommendationStatus.OPEN,
            }
        )
        for rec in output.recommendations
    ]
    for recommendation in recommendations:
        await repositories.recommendations.upsert(recommendation)
    return {"recommendation_ids": [rec.id for rec in recommendations]}


# Step 5 adds Execution (deliverables and proposed actions).
PERSISTERS: dict[AgentName, Persister] = {AgentName.STRATEGY: persist_strategy}
