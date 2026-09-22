"""Centralized idempotent index setup for all owned collections."""

from typing import Protocol

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.deliverables import DeliverablesRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.proposed_actions import ProposedActionsRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.runs import RunsRepository
from app.intelligence.repositories.sessions import SessionsRepository
from app.intelligence.repositories.trends import TrendsRepository


class IndexRepository(Protocol):
    async def ensure_indexes(self) -> None: ...


def repository_set(database: AsyncDatabase[Document]) -> tuple[IndexRepository, ...]:
    return (
        CompaniesRepository(database),
        CompetitorsRepository(database),
        CompetitorActivitiesRepository(database),
        TrendsRepository(database),
        InfluencersRepository(database),
        SessionsRepository(database),
        RunsRepository(database),
        RecommendationsRepository(database),
        DeliverablesRepository(database),
        ProposedActionsRepository(database),
    )


async def ensure_indexes(database: AsyncDatabase[Document]) -> None:
    for repository in repository_set(database):
        await repository.ensure_indexes()
