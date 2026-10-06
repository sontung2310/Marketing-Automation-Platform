"""Repository for agent runs."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Run
from app.intelligence.repositories.base import Document, Repository


class RunsRepository(Repository[Run]):
    collection_name = "runs"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Run)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("session_id", ASCENDING), ("started_at", DESCENDING)],
                name="session_started",
            )
        ]

    async def set_events(self, run_id: str, events: list[dict[str, object]]) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"events": events}})

    async def list_for_session(self, session_id: str, *, limit: int = 100) -> list[Run]:
        documents = (
            self.collection.find({"session_id": session_id})
            .sort("started_at", ASCENDING)
            .limit(limit)
        )
        return [self.model_type.model_validate(document) async for document in documents]
