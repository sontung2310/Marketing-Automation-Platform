"""Typed repositories for platform-owned collections."""

from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.deliverables import DeliverablesRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.proposed_actions import ProposedActionsRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.runs import RunsRepository
from app.intelligence.repositories.sessions import SessionsRepository
from app.intelligence.repositories.trends import TrendsRepository

__all__ = [
    "CompaniesRepository",
    "CompetitorActivitiesRepository",
    "CompetitorsRepository",
    "DeliverablesRepository",
    "InfluencersRepository",
    "ProposedActionsRepository",
    "RecommendationsRepository",
    "RunsRepository",
    "SessionsRepository",
    "TrendsRepository",
]
