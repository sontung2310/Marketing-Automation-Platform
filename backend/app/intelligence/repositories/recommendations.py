"""Repository for persisted strategy recommendations."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Recommendation
from app.intelligence.repositories.base import Document, Repository


class RecommendationsRepository(Repository[Recommendation]):
    collection_name = "recommendations"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Recommendation)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("run_id", ASCENDING), ("ordinal", ASCENDING)],
                name="run_ordinal_unique",
                unique=True,
            )
        ]
