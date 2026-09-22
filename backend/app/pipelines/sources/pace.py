"""Typed, read-only access to Pace's AI-enriched posts."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.repositories.base import Document

logger = logging.getLogger(__name__)
PACE_COLLECTION: Final = "ai_posts"


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class PaceKeyword(SourceModel):
    term: str | None = None
    score: int | float | None = None


class PaceSentiment(SourceModel):
    label: str | None = None
    score: int | float | None = None


class PacePost(SourceModel):
    source_id: str = Field(min_length=1)
    created_at: datetime
    topics: list[str] = Field(default_factory=list)
    keywords: list[PaceKeyword] = Field(default_factory=list)
    source: str = Field(min_length=1)
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    sentiment: PaceSentiment | None = None

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


@dataclass(frozen=True)
class PaceReadResult:
    posts: list[PacePost]
    skipped: int = 0


def _source_id(value: object) -> str | None:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and value:
        return value
    return None


async def _read_documents(
    collection: AsyncCollection[Document], *, window_start: datetime, window_end: datetime
) -> list[Document]:
    query: Document = {"created_at": {"$gte": window_start, "$lt": window_end}}
    cursor = collection.find(query).sort([("created_at", -1), ("_id", 1)])
    return [document async for document in cursor]


def _post_from_document(document: Document) -> PacePost:
    source_id = _source_id(document.get("_id"))
    if source_id is None:
        raise ValueError("Pace post is missing _id")
    return PacePost.model_validate({**document, "source_id": source_id})


class PaceSource:
    """Read posts from one captured UTC window without mutating Pace."""

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        self.database = database

    async def read(self, *, window_start: datetime, window_end: datetime) -> PaceReadResult:
        posts: list[PacePost] = []
        skipped = 0
        for document in await _read_documents(
            self.database[PACE_COLLECTION], window_start=window_start, window_end=window_end
        ):
            source_id = _source_id(document.get("_id")) or "<missing>"
            try:
                posts.append(_post_from_document(document))
            except (TypeError, ValueError) as error:
                skipped += 1
                logger.warning(
                    "Skipping malformed Pace post %s: %s",
                    source_id,
                    error,
                    extra={"ctx": {"source_id": source_id}},
                )
        return PaceReadResult(posts=posts, skipped=skipped)
