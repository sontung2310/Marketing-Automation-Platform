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
