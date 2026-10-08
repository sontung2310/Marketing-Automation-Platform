"""Typed, read-only access to Data-Crawler-Task influencer candidates."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.repositories.base import Document

logger = logging.getLogger(__name__)

DCT_COMPANY_ID: Final = "marketingeye.com.au"
DCT_CANDIDATE_LIMIT: Final = 10


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SourcePost(SourceModel):
    text: str | None = None
    url: str | None = None
    likes: int | float | None = None
    replies: int | float | None = None
    reposts: int | float | None = None


class DctCandidate(SourceModel):
    source_id: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    handle: str = Field(min_length=1)
    profile_url: str = Field(min_length=1)
    followers: int | float | None = None
    avatar_url: str | None = None
    recent_posts: list[SourcePost] = Field(default_factory=list)
    latest_final_score: int | float
    topic_relevance: int | float | None = None


@dataclass(frozen=True)
class DctReadResult:
    candidates: list[DctCandidate]
    skipped: int = 0


def _source_id(value: object) -> str | None:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and value:
        return value
    return None


async def _read_documents(collection: AsyncCollection[Document]) -> list[Document]:
    query: Document = {
        "company_id": DCT_COMPANY_ID,
        "evaluation.status": "eligible",
        "evaluation.latest_final_score": {"$type": "number"},
    }
    cursor = (
        collection.find(query)
        # A missing follower count sorts last in descending order.
        .sort([("evaluation.latest_final_score", -1), ("profile.followers", -1), ("_id", 1)])
        .limit(DCT_CANDIDATE_LIMIT)
    )
    return [document async for document in cursor]


def _candidate_from_document(document: Document) -> DctCandidate:
    source_id = _source_id(document.get("_id"))
    if source_id is None:
        raise ValueError("candidate is missing _id")
    profile = document.get("profile")
    account = document.get("account")
    evaluation = document.get("evaluation")
    platform_data = document.get("platform_data")
    if not isinstance(profile, dict) or not isinstance(account, dict):
        raise ValueError("candidate profile or account is malformed")
    if not isinstance(evaluation, dict) or not isinstance(platform_data, dict):
        raise ValueError("candidate evaluation or platform_data is malformed")
    posts = platform_data.get("recent_posts", [])
    if not isinstance(posts, list):
        raise ValueError("candidate recent_posts is malformed")
    return DctCandidate.model_validate(
        {
            "source_id": source_id,
            "platform": document.get("platform"),
            "display_name": profile.get("display_name"),
            "handle": account.get("handle"),
            "profile_url": account.get("profile_url"),
            "followers": profile.get("followers"),
            "avatar_url": profile.get("avatar_url") or None,
            "recent_posts": posts,
            "latest_final_score": evaluation.get("latest_final_score"),
            "topic_relevance": (evaluation.get("score_breakdown") or {}).get("topic_relevance")
            if isinstance(evaluation.get("score_breakdown"), dict)
            else None,
        }
    )


class DctSource:
    """Read the bounded, tenant-scoped DCT candidate set without writing."""

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        self.database = database

    async def read(self) -> DctReadResult:
        candidates: list[DctCandidate] = []
        skipped = 0
        for document in await _read_documents(self.database["influencer_candidates"]):
            source_id = _source_id(document.get("_id")) or "<missing>"
            try:
                candidates.append(_candidate_from_document(document))
            except (TypeError, ValueError) as error:
                skipped += 1
                logger.warning(
                    "Skipping malformed DCT candidate %s: %s",
                    source_id,
                    error,
                    extra={"ctx": {"source_id": source_id}},
                )
        return DctReadResult(candidates=candidates, skipped=skipped)
