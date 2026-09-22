"""Repository for actions awaiting approval or mock execution."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import ProposedAction
from app.intelligence.repositories.base import Document, Repository


class ProposedActionsRepository(Repository[ProposedAction]):
    collection_name = "proposed_actions"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, ProposedAction)

    def index_models(self) -> list[IndexModel]:
        return [
            IndexModel(
                [("deliverable_id", ASCENDING), ("status", ASCENDING)],
                name="deliverable_status",
            )
        ]
