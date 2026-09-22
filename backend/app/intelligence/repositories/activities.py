"""Repository for the competitor activity feed."""

from pymongo import IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import CompetitorActivity
from app.intelligence.repositories.base import Document, Repository, company_feed_indexes


class CompetitorActivitiesRepository(Repository[CompetitorActivity]):
    collection_name = "competitor_activities"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, CompetitorActivity)

    def index_models(self) -> list[IndexModel]:
        return company_feed_indexes()
