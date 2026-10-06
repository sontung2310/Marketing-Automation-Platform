"""Repository for agent runs."""

from datetime import datetime
from typing import cast

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Run, RunStatus
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
            ),
            IndexModel([("started_at", DESCENDING)], name="started_at"),  # daily run cap
        ]

    async def set_events(self, run_id: str, events: list[dict[str, object]]) -> None:
        await self.collection.update_one({"_id": run_id}, {"$set": {"events": events}})

    async def replace_if_running(self, run: Run) -> bool:
        """Write a run's final state unless it already ended (e.g. read as interrupted)."""
        result = await self.collection.replace_one(
            {"_id": run.id, "status": RunStatus.RUNNING},
            cast(Document, run.model_dump(by_alias=True, mode="python")),
        )
        return result.matched_count == 1

    async def list_for_session(self, session_id: str, *, limit: int = 100) -> list[Run]:
        """The session's latest `limit` runs, oldest first."""
        documents = (
            self.collection.find({"session_id": session_id})
            .sort("started_at", DESCENDING)
            .limit(limit)
        )
        runs = [self.model_type.model_validate(document) async for document in documents]
        return runs[::-1]

    async def count_started_since(self, since: datetime) -> int:
        return await self.collection.count_documents({"started_at": {"$gte": since}})
