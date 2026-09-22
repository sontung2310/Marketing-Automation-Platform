"""Repository for chat sessions."""

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Session
from app.intelligence.repositories.base import Document, Repository


class SessionsRepository(Repository[Session]):
    collection_name = "sessions"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Session)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("company_id", ASCENDING), ("created_at", DESCENDING)],
                name="company_created",
            )
        ]
