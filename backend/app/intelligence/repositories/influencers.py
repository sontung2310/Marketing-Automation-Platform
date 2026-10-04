"""Repository for normalized influencers."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Channel, Influencer
from app.intelligence.repositories.base import Document, TenantRepository


class InfluencersRepository(TenantRepository[Influencer]):
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
            IndexModel([("name", "text"), ("topics", "text")], name="influencer_text"),
        ]

    async def search_for_company(
        self,
        company_id: str,
        *,
        limit: int,
        topic: str | None = None,
        channels: list[Channel] | None = None,
        region: str | None = None,
        min_followers: int | None = None,
    ) -> list[Influencer]:
        filters: Document = {"company_id": company_id}
        if topic:
            filters["$text"] = {"$search": topic}
        if channels:
            filters["channel"] = {"$in": [item.value for item in channels]}
        if region:
            filters["audience_region"] = region
        if min_followers is not None:
            filters["followers"] = {"$gte": min_followers}
        documents = self.collection.find(filters).sort("relevance_score", DESCENDING).limit(limit)
        return [self.model_type.model_validate(document) async for document in documents]
