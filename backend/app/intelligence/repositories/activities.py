"""Repository for the competitor activity feed."""

from datetime import datetime

from pymongo import DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import (
    ActivitySummary,
    ActivityType,
    Channel,
    CompetitorActivity,
)
from app.intelligence.repositories.base import Document, TenantRepository, company_feed_indexes


class CompetitorActivitiesRepository(TenantRepository[CompetitorActivity]):
    collection_name = "competitor_activities"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, CompetitorActivity)

    def index_models(self) -> list[IndexModel]:
        return company_feed_indexes()

    async def search_for_company(
        self,
        company_id: str,
        *,
        detected_since: datetime,
        limit: int,
        query: str | None = None,
        competitor_ids: list[str] | None = None,
        activity_types: list[ActivityType] | None = None,
        channels: list[Channel] | None = None,
    ) -> list[CompetitorActivity]:
        filters: Document = {
            "company_id": company_id,
            "detected_at": {"$gte": detected_since},
        }
        if query:
            filters["$text"] = {"$search": query}
        if competitor_ids:
            filters["competitor_id"] = {"$in": competitor_ids}
        if activity_types:
            filters["activity_type"] = {"$in": [item.value for item in activity_types]}
        if channels:
            filters["channel"] = {"$in": [item.value for item in channels]}
        documents = self.collection.find(filters).sort("detected_at", DESCENDING).limit(limit)
        return [self.model_type.model_validate(document) async for document in documents]

    async def summarize_for_company(
        self, company_id: str, *, detected_since: datetime
    ) -> ActivitySummary:
        pipeline: list[Document] = [
            {"$match": {"company_id": company_id, "detected_at": {"$gte": detected_since}}},
            {
                "$facet": {
                    "counts": [
                        {
                            "$group": {
                                "_id": {
                                    "competitor_id": "$competitor_id",
                                    "competitor_name": "$competitor_name",
                                    "activity_type": "$activity_type",
                                },
                                "count": {"$sum": 1},
                            }
                        },
                        {"$sort": {"_id.competitor_name": 1, "_id.activity_type": 1}},
                        {
                            "$project": {
                                "_id": 0,
                                "competitor_id": "$_id.competitor_id",
                                "competitor_name": "$_id.competitor_name",
                                "activity_type": "$_id.activity_type",
                                "count": 1,
                            }
                        },
                    ],
                    "recent_items": [
                        {"$sort": {"detected_at": -1}},
                        {
                            "$group": {
                                "_id": {
                                    "competitor_id": "$competitor_id",
                                    "competitor_name": "$competitor_name",
                                },
                                "items": {"$firstN": {"input": "$$ROOT", "n": 3}},
                            }
                        },
                        {
                            "$project": {
                                "_id": 0,
                                "competitor_id": "$_id.competitor_id",
                                "competitor_name": "$_id.competitor_name",
                                "items": 1,
                            }
                        },
                    ],
                }
            },
        ]
        cursor = await self.collection.aggregate(pipeline)
        documents = await cursor.to_list(length=1)
        if not documents:
            return ActivitySummary()
        return ActivitySummary.model_validate(documents[0])
