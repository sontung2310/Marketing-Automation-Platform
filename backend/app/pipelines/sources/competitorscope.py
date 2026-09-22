"""Typed, read-only access to the verified CompetitorScope source collections."""

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
MARKETING_EYE_SOURCE_NAME: Final = "Marketing Eye"


class SourceModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SourceCompany(SourceModel):
    source_id: str = Field(alias="_id")
    name: str


class SourceCompetitor(SourceModel):
    source_id: str = Field(alias="_id")
    name: str
    website_url: str | None = None
    company_id: str | None = None


class SourceMonitoringTarget(SourceModel):
    source_id: str = Field(alias="_id")
    competitor_id: str
    url: str | None = None


class SourceChange(SourceModel):
    source_id: str = Field(alias="_id")
    monitoring_target_id: str
    change_type: str | None = None
    summary: str | None = None
    narrative_summary: str | None = None
    detected_url: str | None = None
    detected_at: datetime
    is_simulated: bool = False

    @field_validator("detected_at")
    @classmethod
    def detected_at_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class CompetitorScopeActivity(SourceModel):
    change: SourceChange
    competitor: SourceCompetitor
    target: SourceMonitoringTarget


@dataclass(frozen=True)
class CompetitorScopeReadResult:
    activities: list[CompetitorScopeActivity]
    skipped: int = 0


class CompetitorScopeSourceError(RuntimeError):
    """The source tenant invariant is not safe to use for ingestion."""


def _source_id(value: object) -> str | None:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and value:
        return value
    return None


def _source_id_or_raise(document: Document, field: str) -> str:
    value = _source_id(document.get(field))
    if value is None:
        raise ValueError(f"source document is missing {field}")
    return value


def _object_id(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise CompetitorScopeSourceError(f"source ID is not a valid ObjectId: {value}")
    return ObjectId(value)


async def _read_documents(collection: AsyncCollection[Document], query: Document) -> list[Document]:
    documents: list[Document] = []
    async for document in collection.find(query):
        documents.append(document)
    return documents


class CompetitorScopeSource:
    """Read and join CompetitorScope documents without mutating the source."""

    def __init__(self, database: AsyncDatabase[Document]) -> None:
        self.database = database

    async def read(self) -> CompetitorScopeReadResult:
        company_documents = await _read_documents(
            self.database["companies"], {"name": MARKETING_EYE_SOURCE_NAME}
        )
        if len(company_documents) != 1:
            raise CompetitorScopeSourceError(
                f"expected exactly one {MARKETING_EYE_SOURCE_NAME!r} source company, "
                f"found {len(company_documents)}"
            )

        source_company_id = _source_id_or_raise(company_documents[0], "_id")
        source_company_object_id = _object_id(source_company_id)
        competitor_documents = await _read_documents(
            self.database["competitors"], {"company_id": source_company_object_id}
        )
        competitors: dict[str, SourceCompetitor] = {}
        competitor_source_ids: list[object] = []
        for document in competitor_documents:
            try:
                competitor_id = _source_id_or_raise(document, "_id")
                competitor = SourceCompetitor.model_validate(
                    {
                        "_id": competitor_id,
                        "name": document.get("name", ""),
                        "website_url": document.get("website_url"),
                        "company_id": _source_id(document.get("company_id")),
                    }
                )
            except (ValueError, TypeError) as error:
                logger.warning("Skipping malformed source competitor: %s", error)
                continue
            competitors[competitor.source_id] = competitor
            competitor_source_ids.append(document["_id"])

        target_documents = await _read_documents(
            self.database["monitoring_targets"],
            {"competitor_id": {"$in": competitor_source_ids}},
        )
        targets: dict[str, SourceMonitoringTarget] = {}
        target_source_ids: list[object] = []
        for document in target_documents:
            try:
                target_id = _source_id_or_raise(document, "_id")
                competitor_id = _source_id_or_raise(document, "competitor_id")
                target = SourceMonitoringTarget.model_validate(
                    {
                        "_id": target_id,
                        "competitor_id": competitor_id,
                        "url": document.get("url"),
                    }
                )
            except (ValueError, TypeError) as error:
                logger.warning("Skipping malformed monitoring target: %s", error)
                continue
            targets[target.source_id] = target
            target_source_ids.append(document["_id"])

        change_documents = await _read_documents(
            self.database["changes"],
            {"monitoring_target_id": {"$in": target_source_ids}},
        )
        activities: list[CompetitorScopeActivity] = []
        skipped = 0
        for document in change_documents:
            source_change_id = _source_id(document.get("_id")) or "<missing>"
            try:
                change = SourceChange.model_validate(
                    {
                        "_id": source_change_id,
                        "monitoring_target_id": _source_id_or_raise(
                            document, "monitoring_target_id"
                        ),
                        "change_type": document.get("change_type"),
                        "summary": document.get("summary"),
                        "narrative_summary": document.get("narrative_summary"),
                        "detected_url": document.get("detected_url"),
                        "detected_at": document.get("detected_at"),
                        "is_simulated": document.get("is_simulated", False),
                    }
                )
                target = targets[change.monitoring_target_id]
                competitor = competitors[target.competitor_id]
                if competitor.company_id != source_company_id:
                    raise ValueError("competitor is outside the tenant allowlist")
                activities.append(
                    CompetitorScopeActivity(change=change, competitor=competitor, target=target)
                )
            except (KeyError, TypeError, ValueError) as error:
                skipped += 1
                logger.warning(
                    "Skipping CompetitorScope change %s: %s",
                    source_change_id,
                    error,
                    extra={"ctx": {"source_id": source_change_id}},
                )
        return CompetitorScopeReadResult(activities=activities, skipped=skipped)
