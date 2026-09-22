"""CompetitorScope-to-owned activity normalization and writes."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import (
    ActivityType,
    Channel,
    Competitor,
    CompetitorActivity,
    Provenance,
    SourceSystem,
)
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.base import Document, UpsertResult
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.pipelines.sources.competitorscope import (
    CompetitorScopeActivity,
    CompetitorScopeReadResult,
)

logger = logging.getLogger(__name__)

COMPETITOR_ACTIVITY_TYPES: Mapping[str, ActivityType] = {
    "NEW_BLOG": ActivityType.NEW_BLOG,
    "NEW_PRODUCT": ActivityType.NEW_PRODUCT,
    "PRICE_CHANGE": ActivityType.PRICE_CHANGE,
    "PRODUCT_REMOVED": ActivityType.PRODUCT_REMOVED,
}


class CompetitorScopeReader(Protocol):
    async def read(self) -> CompetitorScopeReadResult: ...


@dataclass(frozen=True)
class PipelineCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.skipped

    def add(self, result: UpsertResult) -> PipelineCounts:
        return PipelineCounts(
            inserted=self.inserted + int(result.inserted),
            updated=self.updated + int(result.updated),
            skipped=self.skipped + int(result.skipped),
        )


@dataclass(frozen=True)
class CompetitorPipelineSummary:
    competitors: PipelineCounts
    activities: PipelineCounts


def title_for_change(activity: CompetitorScopeActivity) -> str:
    change = activity.change
    narrative = change.narrative_summary.strip() if change.narrative_summary else ""
    if narrative:
        title = narrative
    else:
        url = next(
            (
                candidate.strip()
                for candidate in (change.detected_url, activity.target.url)
                if candidate and candidate.strip()
            ),
            "",
        )
        change_type = change.change_type or "CHANGE"
        title = f"{change_type} detected at {url}" if url else f"{change_type} detected"
    return title if len(title) <= 120 else f"{title[:117]}..."


def activity_type_for_change(change_type: str | None) -> ActivityType | None:
    if change_type is None:
        return None
    return COMPETITOR_ACTIVITY_TYPES.get(change_type)


def build_owned_competitor(activity: CompetitorScopeActivity, company_id: str) -> Competitor:
    source = activity.competitor
    if not source.website_url:
        raise ValueError("source competitor is missing website_url")
    return Competitor(
        id=f"cpt_{source.source_id}",
        company_id=company_id,
        name=source.name,
        website=source.website_url,
        is_fictional=False,
        source=Provenance(system=SourceSystem.COMPETITORSCOPE, ref_id=source.source_id),
        is_mock=False,
    )


def build_owned_activity(
    activity: CompetitorScopeActivity,
    *,
    company_id: str,
    competitor_id: str,
    ingested_at: datetime | None = None,
) -> CompetitorActivity | None:
    activity_type = activity_type_for_change(activity.change.change_type)
    if activity_type is None:
        return None
    title = title_for_change(activity)
    change = activity.change
    return CompetitorActivity(
        id=f"act_{change.source_id}",
        company_id=company_id,
        competitor_id=competitor_id,
        competitor_name=activity.competitor.name,
        activity_type=activity_type,
        channel=Channel.WEBSITE,
        title=title,
        summary=change.summary or title,
        narrative_summary=change.narrative_summary,
        url=change.detected_url or activity.target.url,
        occurred_at=change.detected_at,
        detected_at=change.detected_at,
        source=Provenance(system=SourceSystem.COMPETITORSCOPE, ref_id=change.source_id),
        is_mock=False,
        is_simulated=change.is_simulated,
        ingested_at=ingested_at or datetime.now(UTC),
    )


async def run_competitor_activity_pipeline(
    reader: CompetitorScopeReader,
    database: AsyncDatabase[Document],
    *,
    company_id: str = "cmp_marketing_eye",
    ingested_at: datetime | None = None,
) -> CompetitorPipelineSummary:
    """Read CompetitorScope and idempotently write owned competitors and activities."""

    source_result = await reader.read()
    competitor_repository = CompetitorsRepository(database)
    activity_repository = CompetitorActivitiesRepository(database)
    competitor_counts = PipelineCounts()
    activity_counts = PipelineCounts(skipped=source_result.skipped)
    owned_competitor_ids: dict[str, str] = {}

    for source_activity in source_result.activities:
        if activity_type_for_change(source_activity.change.change_type) is None:
            activity_counts = PipelineCounts(
                inserted=activity_counts.inserted,
                updated=activity_counts.updated,
                skipped=activity_counts.skipped + 1,
            )
            logger.warning(
                "Skipping unsupported CompetitorScope change type for %s",
                source_activity.change.source_id,
                extra={"ctx": {"source_id": source_activity.change.source_id}},
            )
            continue

        source_competitor_id = source_activity.competitor.source_id
        try:
            owned_competitor_id = owned_competitor_ids.get(source_competitor_id)
            if owned_competitor_id is None:
                competitor = build_owned_competitor(source_activity, company_id)
                competitor_result = await competitor_repository.upsert_by_source(competitor)
                competitor_counts = competitor_counts.add(competitor_result)
                stored_competitor = await competitor_repository.get_by_source(
                    SourceSystem.COMPETITORSCOPE, source_competitor_id
                )
                if stored_competitor is None:
                    raise RuntimeError("owned competitor disappeared after upsert")
                owned_competitor_id = stored_competitor.id
                owned_competitor_ids[source_competitor_id] = owned_competitor_id

            owned_activity = build_owned_activity(
                source_activity,
                company_id=company_id,
                competitor_id=owned_competitor_id,
                ingested_at=ingested_at,
            )
            if owned_activity is None:
                raise RuntimeError("activity type was not supported")
            activity_result = await activity_repository.upsert_by_source(owned_activity)
            activity_counts = activity_counts.add(activity_result)
        except (RuntimeError, ValueError) as error:
            activity_counts = PipelineCounts(
                inserted=activity_counts.inserted,
                updated=activity_counts.updated,
                skipped=activity_counts.skipped + 1,
            )
            logger.warning(
                "Skipping CompetitorScope change %s: %s",
                source_activity.change.source_id,
                error,
                extra={"ctx": {"source_id": source_activity.change.source_id}},
            )

    return CompetitorPipelineSummary(
        competitors=competitor_counts,
        activities=activity_counts,
    )
