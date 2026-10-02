"""Repository for the competitor activity feed."""

from datetime import datetime

from pymongo import ASCENDING, DESCENDING, IndexModel
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

    async def page_for_company(
        self,
        company_id: str,
        *,
        limit: int,
        after: tuple[datetime, str] | None = None,
        since: datetime | None = None,
        competitor_ids: list[str] | None = None,
        activity_types: list[ActivityType] | None = None,
        channels: list[Channel] | None = None,
    ) -> list[CompetitorActivity]:
        """Feed page, newest first, keyset-paginated on (detected_at, _id)."""
        filters: Document = {"company_id": company_id}
        if since is not None:
            filters["detected_at"] = {"$gte": since}
        if competitor_ids:
            filters["competitor_id"] = {"$in": competitor_ids}
        if activity_types:
            filters["activity_type"] = {"$in": [item.value for item in activity_types]}
        if channels:
            filters["channel"] = {"$in": [item.value for item in channels]}
        if after is not None:
            detected_at, activity_id = after
            filters["$or"] = [
                {"detected_at": {"$lt": detected_at}},
                {"detected_at": detected_at, "_id": {"$lt": activity_id}},
            ]
        documents = (
            self.collection.find(filters)
            .sort([("detected_at", DESCENDING), ("_id", DESCENDING)])
            .limit(limit)
        )
        return [self.model_type.model_validate(document) async for document in documents]

    async def detected_after(
        self, company_id: str, after: datetime, *, limit: int
    ) -> list[CompetitorActivity]:
        """Activities detected after `after`, oldest first (the live stream's poll)."""
        documents = (
            self.collection.find({"company_id": company_id, "detected_at": {"$gt": after}})
            .sort([("detected_at", ASCENDING), ("_id", ASCENDING)])
            .limit(limit)
        )
        return [self.model_type.model_validate(document) async for document in documents]

    async def count_unseen(self, company_id: str) -> int:
        return await self.collection.count_documents({"company_id": company_id, "seen_at": None})

    async def mark_seen(self, company_id: str, *, up_to: datetime, seen_at: datetime) -> int:
        result = await self.collection.update_many(
            {"company_id": company_id, "seen_at": None, "detected_at": {"$lte": up_to}},
            {"$set": {"seen_at": seen_at}},
        )
        return result.modified_count

    async def newest_ingested_at(self, company_id: str) -> datetime | None:
        document = await self.collection.find_one(
            {"company_id": company_id}, {"ingested_at": 1}, sort=[("ingested_at", DESCENDING)]
        )
        value = document.get("ingested_at") if document else None
        return value if isinstance(value, datetime) else None

    async def get_many_for_company(
        self, activity_ids: list[str], company_id: str
    ) -> list[CompetitorActivity]:
        if not activity_ids:
            return []
        documents = self.collection.find({"_id": {"$in": activity_ids}, "company_id": company_id})
        return [self.model_type.model_validate(document) async for document in documents]
