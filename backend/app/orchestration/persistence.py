"""Persist each agent's structured output; the returned IDs join the output.final event."""

from collections.abc import Awaitable, Callable

from app.agents.common.context import AgentOutcome
from app.agents.strategy.output import StrategyOutput
from app.intelligence.models import (
    AgentName,
    Recommendation,
    RecommendationStatus,
    Run,
    RunStatus,
)
from app.orchestration.references import RunRepositories

Persister = Callable[[RunRepositories, Run, AgentOutcome], Awaitable[dict[str, object]]]


async def persist_strategy(
    repositories: RunRepositories, run: Run, outcome: AgentOutcome
) -> dict[str, object]:
    output = outcome.output
    if not isinstance(output, StrategyOutput):
        raise TypeError(f"Strategy runs return StrategyOutput, got {type(output).__name__}")
    if outcome.status is not RunStatus.SUCCEEDED:
        return {"recommendation_ids": []}  # refusals and clarifications recommend nothing
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
    await repositories.recommendations.insert_many(recommendations)
    try:
        # "#N" means the latest Strategy run, so only its set stays OPEN (even an empty one).
        await repositories.recommendations.supersede_open(run.session_id, keep_run_id=run.id)
    except BaseException:
        await repositories.recommendations.delete_for_run(run.id)  # no partial set
        raise
    return {"recommendation_ids": [rec.id for rec in recommendations]}


# Step 5 adds Execution (deliverables and proposed actions).
PERSISTERS: dict[AgentName, Persister] = {AgentName.STRATEGY: persist_strategy}
