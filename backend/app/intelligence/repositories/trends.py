"""Repository for normalized market trends."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Trend
from app.intelligence.repositories.base import Document, Repository


class TrendsRepository(Repository[Trend]):
    collection_name = "trends"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Trend)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("company_id", ASCENDING), ("momentum_pct", DESCENDING)],
                name="company_momentum",
            ),
            IndexModel(
                [("source.system", ASCENDING), ("source.ref_id", ASCENDING)],
                name="source_ref_unique",
                unique=True,
            ),
        ]
