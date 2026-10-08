"""Persist each agent's structured output; the returned IDs join the output.final event."""

from collections.abc import Awaitable, Callable, Mapping

from app.agents.common.context import AgentOutcome
from app.agents.execution.output import ExecutionOutput
from app.agents.strategy.output import StrategyOutput
from app.intelligence.models import (
    AgentName,
    Deliverable,
    Recommendation,
    RecommendationStatus,
    Run,
    RunStatus,
)
from app.orchestration.actions import build_actions
from app.orchestration.references import RunRepositories

# The trigger record lets code fill action payloads (an influencer's name, a recommendation).
Persister = Callable[
    [RunRepositories, Run, AgentOutcome, Mapping[str, object] | None],
    Awaitable[dict[str, object]],
]


async def persist_strategy(
    repositories: RunRepositories,
    run: Run,
    outcome: AgentOutcome,
    trigger: Mapping[str, object] | None,
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
    if not recommendations:
        return {"recommendation_ids": []}  # an answer without recommendations keeps the set
    await repositories.recommendations.insert_many(recommendations)
    try:
        # One company-wide set: the newest run's recommendations replace every other OPEN one.
        session = await repositories.sessions.get(run.session_id)
        if session is None:
            raise RuntimeError(f"run {run.id} has no session")
        await repositories.recommendations.supersede_open(session.company_id, keep_run_id=run.id)
    except BaseException:
        await repositories.recommendations.delete_for_run(run.id)  # no partial set
        raise
    return {"recommendation_ids": [rec.id for rec in recommendations]}


async def persist_execution(
    repositories: RunRepositories,
    run: Run,
    outcome: AgentOutcome,
    trigger: Mapping[str, object] | None,
) -> dict[str, object]:
    output = outcome.output
    if not isinstance(output, ExecutionOutput):
        raise TypeError(f"Execution runs return ExecutionOutput, got {type(output).__name__}")
    if outcome.status is not RunStatus.SUCCEEDED or output.deliverable is None:
        # Refusals and clarifications deliver nothing.
        return {"deliverable_id": None, "proposed_action_ids": [], "proposed_actions": []}
    deliverable = Deliverable.model_validate(
        output.deliverable.model_dump() | {"id": Deliverable.new_id(), "run_id": run.id}
    )
    # Payloads are built and validated before anything is written.
    actions = build_actions(deliverable, output.proposed_actions, trigger=trigger)
    await repositories.deliverables.insert_many([deliverable])
    try:
        await repositories.proposed_actions.insert_many(actions)
    except BaseException:
        await repositories.proposed_actions.delete_for_deliverable(deliverable.id)
        await repositories.deliverables.delete(deliverable.id)  # all or nothing
        raise
    # A recommendation acted on (Do this, or "#N") leaves the Strategy panel.
    trigger_id = trigger.get("id") if trigger else None
    if isinstance(trigger_id, str) and trigger_id.startswith(Recommendation.id_prefix):
        await repositories.recommendations.mark_done(trigger_id)
    return {
        "deliverable_id": deliverable.id,
        "proposed_action_ids": [action.id for action in actions],
        # The persisted records replace the model's proposals in output.final (the UI acts on IDs).
        "proposed_actions": [action.model_dump(mode="json") for action in actions],
    }


PERSISTERS: dict[AgentName, Persister] = {
    AgentName.STRATEGY: persist_strategy,
    AgentName.EXECUTION: persist_execution,
}
