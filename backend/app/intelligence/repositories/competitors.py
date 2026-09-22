"""Repository for the owned competitors collection."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Competitor
from app.intelligence.repositories.base import Document, Repository


class CompetitorsRepository(Repository[Competitor]):
    collection_name = "competitors"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Competitor)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel([("company_id", ASCENDING), ("name", ASCENDING)], name="company_name"),
            IndexModel(
                [("source.system", ASCENDING), ("source.ref_id", ASCENDING)],
                name="source_ref_unique",
                unique=True,
            ),
        ]

    async def list_for_company(self, company_id: str, *, limit: int = 100) -> list[Competitor]:
        if limit < 1:
            return []
        documents = self.collection.find({"company_id": company_id}).limit(limit)
        return [self.model_type.model_validate(document) async for document in documents]
