"""Repository for persisted strategy recommendations."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Recommendation, RecommendationStatus, Run
from app.intelligence.repositories.base import Document, Repository
from app.intelligence.repositories.runs import RunsRepository
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
            ),
            IndexModel(
                [("session_id", ASCENDING), ("status", ASCENDING)], name="session_status"
            ),  # supersede_open
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

    async def supersede_open(self, session_id: str, *, keep_run_id: str) -> None:
        """Mark the session's other OPEN recommendations SUPERSEDED."""
        await self.collection.update_many(
            {
                "session_id": session_id,
                "run_id": {"$ne": keep_run_id},
                "status": RecommendationStatus.OPEN.value,
            },
            {"$set": {"status": RecommendationStatus.SUPERSEDED.value}},
        )

    async def delete_for_run(self, run_id: str) -> None:
        await self.collection.delete_many({"run_id": run_id})

    async def list_for_company(
        self, company_id: str, *, status: RecommendationStatus, limit: int
    ) -> list[tuple[Recommendation, Run]]:
        """The company's recommendations, newest run first, each with its run."""
        pipeline: list[Document] = [
            {"$match": {"status": status.value}},
            {
                "$lookup": {
                    "from": SessionsRepository.collection_name,
                    "localField": "session_id",
                    "foreignField": "_id",
                    "as": "session",
                }
            },
            {"$match": {"session.company_id": company_id}},
            {
                "$lookup": {
                    "from": RunsRepository.collection_name,
                    "localField": "run_id",
                    "foreignField": "_id",
                    "as": "run",
                }
            },
            {"$unwind": "$run"},
            {"$sort": {"run.started_at": -1, "ordinal": 1}},
            {"$limit": limit},
            {"$project": {"session": 0}},
        ]
        cursor = await self.collection.aggregate(pipeline)
        results: list[tuple[Recommendation, Run]] = []
        async for document in cursor:
            run = document.pop("run")
            results.append((self.model_type.model_validate(document), Run.model_validate(run)))
        return results
