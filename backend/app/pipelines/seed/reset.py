"""Wipe one company's session/run history for a clean demo re-run (roadmap 8.2)."""

from __future__ import annotations

from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.deliverables import DeliverablesRepository
from app.intelligence.repositories.proposed_actions import ProposedActionsRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.runs import RunsRepository
from app.intelligence.repositories.sessions import SessionsRepository


@dataclass(frozen=True)
class ResetCounts:
    sessions: int = 0
    runs: int = 0
    recommendations: int = 0
    deliverables: int = 0
    proposed_actions: int = 0
    simulated_activities: int = 0


async def reset_demo_state(database: AsyncDatabase[Document], company_id: str) -> ResetCounts:
    """Delete every session, run, recommendation, deliverable, action and simulated
    activity the company has accumulated, so a re-seed starts from a clean slate.
    Never touches competitors, trends, influencers or non-simulated activity -
    those are re-synced by the seed and the pipelines, not cleared here."""
    sessions = SessionsRepository(database)
    runs = RunsRepository(database)
    recommendations = RecommendationsRepository(database)
    deliverables = DeliverablesRepository(database)
    proposed_actions = ProposedActionsRepository(database)
    activities = CompetitorActivitiesRepository(database)

    session_ids = await sessions.ids_matching({"company_id": company_id})
    run_ids = await runs.ids_matching({"session_id": {"$in": session_ids}})
    deliverable_ids = await deliverables.ids_matching({"run_id": {"$in": run_ids}})

    return ResetCounts(
        proposed_actions=await proposed_actions.delete_many(
            {"deliverable_id": {"$in": deliverable_ids}}
        ),
        deliverables=await deliverables.delete_many({"_id": {"$in": deliverable_ids}}),
        recommendations=await recommendations.delete_many({"session_id": {"$in": session_ids}}),
        runs=await runs.delete_many({"_id": {"$in": run_ids}}),
        sessions=await sessions.delete_many({"company_id": company_id}),
        simulated_activities=await activities.delete_many(
            {"company_id": company_id, "is_simulated": True}
        ),
    )
