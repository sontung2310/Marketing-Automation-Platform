"""Repository for actions awaiting approval or mock execution."""

from pymongo import ASCENDING, IndexModel, ReturnDocument
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import ProposedAction, ProposedActionStatus
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

    async def delete_for_deliverable(self, deliverable_id: str) -> None:
        await self.collection.delete_many({"deliverable_id": deliverable_id})

    async def transition(
        self,
        action_id: str,
        from_status: ProposedActionStatus,
        update: dict[str, object],
    ) -> ProposedAction | None:
        """Apply the update only if the action is still in from_status (one atomic write),
        so two concurrent approvals cannot both run the connector."""
        document = await self.collection.find_one_and_update(
            {"_id": action_id, "status": from_status},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        )
        return None if document is None else ProposedAction.model_validate(document)
