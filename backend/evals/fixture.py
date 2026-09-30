"""Versioned eval fixtures (data-contract §6): the committed seed plus adversarial records.

Timestamps are stored as authored and shifted to "now" on install, so recency rules
(the 21-day staleness check) behave the same on every eval run.
"""

import json
from datetime import datetime
from functools import cached_property
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.core.db import Database
from app.intelligence.models import (
    Company,
    Competitor,
    CompetitorActivity,
    Influencer,
    PrefixedModel,
    Trend,
)
from app.intelligence.repositories import (
    CompaniesRepository,
    CompetitorActivitiesRepository,
    CompetitorsRepository,
    InfluencersRepository,
    TrendsRepository,
)
from app.intelligence.repositories.indexes import ensure_indexes
from app.pipelines.seed.loader import shift_datetimes

EVALUATION_DIR = Path(__file__).resolve().parents[2] / "evaluation"
FIXTURES_DIR = EVALUATION_DIR / "fixtures"


class FixtureBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    snapshot_at: datetime
    companies: list[Company]
    competitors: list[Competitor]
    competitor_activities: list[CompetitorActivity]
    trends: list[Trend]
    influencers: list[Influencer]

    @cached_property
    def by_id(self) -> dict[str, PrefixedModel]:
        records: list[PrefixedModel] = [
            *self.companies,
            *self.competitors,
            *self.competitor_activities,
            *self.trends,
            *self.influencers,
        ]
        return {record.id: record for record in records}

    def ids(self) -> set[str]:
        return set(self.by_id)

    def record(self, record_id: str) -> dict[str, object] | None:
        """One record as JSON-ready data (the shape MCP tools return), or None."""
        record = self.by_id.get(record_id)
        return record.model_dump(mode="json") if record else None


def fixture_path(version: str) -> Path:
    return FIXTURES_DIR / f"{version}.json"


def load_fixture(version: str) -> FixtureBundle:
    return FixtureBundle.model_validate(json.loads(fixture_path(version).read_text("utf-8")))


def shifted_to(fixture: FixtureBundle, when: datetime) -> FixtureBundle:
    """The fixture as if snapshotted at `when` (an eval run's start). The agent, the checks
    and the judge must all read this same shifted copy."""
    return shift_datetimes(fixture, offset=when - fixture.snapshot_at)


async def install_fixture(database: Database, shifted: FixtureBundle) -> None:
    """Write an already-shifted fixture into an empty database."""
    await ensure_indexes(database)
    await CompaniesRepository(database).insert_many(shifted.companies)
    await CompetitorsRepository(database).insert_many(shifted.competitors)
    await CompetitorActivitiesRepository(database).insert_many(shifted.competitor_activities)
    await TrendsRepository(database).insert_many(shifted.trends)
    await InfluencersRepository(database).insert_many(shifted.influencers)
