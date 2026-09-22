"""Idempotent writes for the validated demo seed."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TypeVar

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import ModelBase
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.base import Document, Repository, UpsertResult
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.indexes import ensure_indexes
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.trends import TrendsRepository
from app.pipelines.seed.loader import SeedBundle, SeedCoverage, validate_seed_bundle

ModelT = TypeVar("ModelT", bound=ModelBase)


@dataclass(frozen=True)
class WriteCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    def add(self, result: UpsertResult) -> WriteCounts:
        return WriteCounts(
            inserted=self.inserted + int(result.inserted),
            updated=self.updated + int(result.updated),
            skipped=self.skipped + int(result.skipped),
        )

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.skipped


@dataclass(frozen=True)
class SeedRunSummary:
    coverage: SeedCoverage
    collections: dict[str, WriteCounts]

    def as_dict(self) -> dict[str, object]:
        return {
            "coverage": asdict(self.coverage),
            "collections": {
                name: {**asdict(counts), "total": counts.total}
                for name, counts in self.collections.items()
            },
        }


async def seed_database(database: AsyncDatabase[Document], bundle: SeedBundle) -> SeedRunSummary:
    """Validate, index and upsert all owned records."""

    coverage = validate_seed_bundle(bundle)
    await ensure_indexes(database)
    collection_counts: dict[str, WriteCounts] = {}

    company_repository = CompaniesRepository(database)
    collection_counts["companies"] = await _upsert_by_id(company_repository, bundle.companies)

    competitor_repository = CompetitorsRepository(database)
    collection_counts["competitors"] = await _upsert_by_source(
        competitor_repository, bundle.competitors
    )

    activity_repository = CompetitorActivitiesRepository(database)
    collection_counts["competitor_activities"] = await _upsert_by_source(
        activity_repository, bundle.competitor_activities
    )

    trend_repository = TrendsRepository(database)
    collection_counts["trends"] = await _upsert_by_source(trend_repository, bundle.trends)

    influencer_repository = InfluencersRepository(database)
    collection_counts["influencers"] = await _upsert_by_source(
        influencer_repository, bundle.influencers
    )
    collection_counts["simulation_templates"] = WriteCounts(
        skipped=len(bundle.simulation_templates)
    )
    return SeedRunSummary(coverage=coverage, collections=collection_counts)


async def _upsert_by_id(repository: Repository[ModelT], models: list[ModelT]) -> WriteCounts:
    counts = WriteCounts()
    for model in models:
        counts = counts.add(await repository.upsert(model))
    return counts


async def _upsert_by_source(repository: Repository[ModelT], models: list[ModelT]) -> WriteCounts:
    counts = WriteCounts()
    for model in models:
        counts = counts.add(await repository.upsert_by_source(model))
    return counts
