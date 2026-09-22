"""Dispatch the intelligence pipelines in a deterministic order."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Final, cast

from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.indexes import ensure_indexes
from app.pipelines.competitor_activity import run_competitor_activity_pipeline
from app.pipelines.influencers import run_influencer_pipeline
from app.pipelines.sources.competitorscope import CompetitorScopeSource
from app.pipelines.sources.dct import DctSource
from app.pipelines.sources.pace import PaceSource
from app.pipelines.trends import run_trend_pipeline

PIPELINE_ORDER: Final[tuple[str, ...]] = ("competitor_activity", "influencers", "trends")


def selected_pipelines(only: str | None = None) -> tuple[str, ...]:
    if only is None:
        return PIPELINE_ORDER
    if only not in PIPELINE_ORDER:
        choices = ", ".join(PIPELINE_ORDER)
        raise ValueError(f"unsupported pipeline {only!r}; choose one of: {choices}")
    return (only,)


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(cast(Any, value)).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


async def run_pipelines(
    *,
    owned_database: AsyncDatabase[Document],
    competitorscope_database: AsyncDatabase[Document],
    dct_database: AsyncDatabase[Document],
    pace_database: AsyncDatabase[Document],
    only: str | None = None,
    company_id: str | None = None,
) -> dict[str, object]:
    """Run selected pipelines and return JSON-safe summaries."""

    settings = get_settings()
    selected = selected_pipelines(only)
    await ensure_indexes(owned_database)
    summaries: dict[str, object] = {}
    tenant_id = company_id or settings.default_company_id
    for pipeline_name in selected:
        summary: object
        if pipeline_name == "competitor_activity":
            summary = await run_competitor_activity_pipeline(
                CompetitorScopeSource(competitorscope_database),
                owned_database,
                company_id=tenant_id,
            )
        elif pipeline_name == "influencers":
            summary = await run_influencer_pipeline(
                DctSource(dct_database), owned_database, company_id=tenant_id
            )
        else:
            summary = await run_trend_pipeline(
                PaceSource(pace_database), owned_database, company_id=tenant_id
            )
        summaries[pipeline_name] = _jsonable(summary)
    return summaries
