"""Repository for execution deliverables."""

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Deliverable
from app.intelligence.repositories.base import Document, Repository


class DeliverablesRepository(Repository[Deliverable]):
    collection_name = "deliverables"

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        super().__init__(database, Deliverable)

    def index_models(self) -> list[IndexModel]:
        return [IndexModel([("run_id", ASCENDING)], name="run")]
