"""Repository for persisted strategy recommendations."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Recommendation
from app.intelligence.repositories.base import Document, Repository
from app.intelligence.repositories.sessions import SessionsRepository


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

    async def get_for_company(
        self, recommendation_id: str, company_id: str
    ) -> Recommendation | None:
        pipeline: list[Document] = [
            {"$match": {"_id": recommendation_id}},
            {
                "$lookup": {
                    "from": SessionsRepository.collection_name,
                    "localField": "session_id",
                    "foreignField": "_id",
                    "as": "session",
                }
            },
            {"$unwind": "$session"},
            {"$match": {"session.company_id": company_id}},
            {"$project": {"session": 0}},
        ]
        cursor = await self.collection.aggregate(pipeline)
        documents = await cursor.to_list(length=1)
        if not documents:
            return None
        return self.model_type.model_validate(documents[0])
