"""Repository for normalized influencers."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Influencer
from app.intelligence.repositories.base import Document, Repository


class InfluencersRepository(Repository[Influencer]):
    collection_name = "influencers"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Influencer)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("company_id", ASCENDING), ("relevance_score", DESCENDING)],
                name="company_relevance",
            ),
            IndexModel(
                [("source.system", ASCENDING), ("source.ref_id", ASCENDING)],
                name="source_ref_unique",
                unique=True,
            ),
        ]
