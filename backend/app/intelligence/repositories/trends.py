"""Repository for normalized market trends."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Channel, Trend, TrendDirection
from app.intelligence.repositories.base import Document, TenantRepository


class TrendsRepository(TenantRepository[Trend]):
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
            IndexModel([("topic", "text"), ("keywords", "text")], name="trend_text"),
        ]

    async def search_for_company(
        self,
        company_id: str,
        *,
        limit: int,
        query: str | None = None,
        channels: list[Channel] | None = None,
        direction: TrendDirection | None = None,
    ) -> list[Trend]:
        filters: Document = {"company_id": company_id}
        if query:
            filters["$text"] = {"$search": query}
        if channels:
            filters["channel"] = {"$in": [item.value for item in channels]}
        if direction is not None:
            filters["direction"] = direction.value
        documents = self.collection.find(filters).sort("momentum_pct", DESCENDING).limit(limit)
        return [self.model_type.model_validate(document) async for document in documents]
