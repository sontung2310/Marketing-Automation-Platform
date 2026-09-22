"""Shared typed repository primitives for owned MongoDB collections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import ModelBase, Provenance, SourceSystem

Document = dict[str, object]
ModelT = TypeVar("ModelT", bound=ModelBase)


@dataclass(frozen=True)
class UpsertResult:
    inserted: bool
    updated: bool

    @property
    def skipped(self) -> bool:
        return not self.inserted and not self.updated


class Repository(Generic[ModelT]):
    """Typed Mongo operations shared by collection-specific repositories."""

    collection_name: str

    def __init__(self, database: AsyncDatabase[Document], model_type: type[ModelT]) -> None:
        self.database = database
        self.model_type = model_type

    @property
    def collection(self) -> AsyncCollection[Document]:
        return self.database[self.collection_name]

    def index_models(self) -> list[IndexModel]:
        return []

    async def ensure_indexes(self) -> None:
        indexes = self.index_models()
        if indexes:
            await self.collection.create_indexes(indexes)

    async def get(self, document_id: str) -> ModelT | None:
        document = await self.collection.find_one({"_id": document_id})
        if document is None:
            return None
        return self.model_type.model_validate(document)

    async def get_by_source(self, system: SourceSystem, ref_id: str) -> ModelT | None:
        document = await self.collection.find_one(
            {"source.system": system, "source.ref_id": ref_id}
        )
        if document is None:
            return None
        return self.model_type.model_validate(document)

    async def list(self, *, limit: int = 100) -> list[ModelT]:
        if limit < 1:
            return []
        documents = self.collection.find({}).limit(limit)
        return [self.model_type.model_validate(document) async for document in documents]

    async def upsert(self, model: ModelT) -> UpsertResult:
        result = await self.collection.replace_one(
            {"_id": model.model_dump(by_alias=True)["_id"]},
            cast(Document, model.model_dump(by_alias=True, mode="python")),
            upsert=True,
        )
        return UpsertResult(
            inserted=result.upserted_id is not None,
            updated=result.upserted_id is None and result.modified_count > 0,
        )

    async def upsert_by_source(self, model: ModelT) -> UpsertResult:
        source = getattr(model, "source", None)
        if not isinstance(source, Provenance):
            raise TypeError(f"{self.collection_name} records require a source provenance")
        model_document = model.model_dump(by_alias=True, mode="python")
        document_id = model_document["_id"]
        document = {key: value for key, value in model_document.items() if key != "_id"}
        result = await self.collection.update_one(
            {"source.system": source.system, "source.ref_id": source.ref_id},
            {
                "$set": cast(Document, document),
                "$setOnInsert": {"_id": document_id},
            },
            upsert=True,
        )
        return UpsertResult(
            inserted=result.upserted_id is not None,
            updated=result.upserted_id is None and result.modified_count > 0,
        )


def company_feed_indexes() -> list[IndexModel]:
    return [
        IndexModel(
            [("company_id", ASCENDING), ("detected_at", DESCENDING)],
            name="company_detected_at",
        ),
        IndexModel(
            [("company_id", ASCENDING), ("activity_type", ASCENDING), ("detected_at", DESCENDING)],
            name="company_activity_type_detected_at",
        ),
        IndexModel(
            [("company_id", ASCENDING), ("competitor_id", ASCENDING), ("detected_at", DESCENDING)],
            name="company_competitor_detected_at",
        ),
        IndexModel(
            [("source.system", ASCENDING), ("source.ref_id", ASCENDING)],
            name="source_ref_unique",
            unique=True,
        ),
        IndexModel(
            [
                ("title", "text"),
                ("summary", "text"),
                ("narrative_summary", "text"),
                ("content_excerpt", "text"),
                ("topics", "text"),
            ],
            name="activity_text",
        ),
    ]
