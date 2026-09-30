"""Versioned eval fixtures (data-contract §6): the committed seed plus adversarial records.

Timestamps are stored as authored and shifted to "now" on install, so recency rules
(the 21-day staleness check) behave the same on every eval run.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.core.db import Database
from app.intelligence.models import Company, Competitor, CompetitorActivity, Influencer, Trend
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

    def ids(self) -> set[str]:
        records = (
            self.companies
            + self.competitors
            + self.competitor_activities
            + self.trends
            + self.influencers
        )
        return {record.id for record in records}

    def record(self, record_id: str) -> dict[str, object] | None:
        """One record as JSON-ready data (the shape MCP tools return), or None."""
        for records in (
            self.companies,
            self.competitors,
            self.competitor_activities,
            self.trends,
            self.influencers,
        ):
            for record in records:
                if record.id == record_id:
                    return record.model_dump(mode="json")
        return None


def fixture_path(version: str) -> Path:
    return FIXTURES_DIR / f"{version}.json"


def load_fixture(version: str) -> FixtureBundle:
    return FixtureBundle.model_validate(json.loads(fixture_path(version).read_text("utf-8")))


async def install_fixture(database: Database, fixture: FixtureBundle) -> None:
    """Write the fixture, shifted to now, into an empty database."""
    shifted = shift_datetimes(fixture, offset=datetime.now(UTC) - fixture.snapshot_at)
    await ensure_indexes(database)
    await CompaniesRepository(database).insert_many(shifted.companies)
    await CompetitorsRepository(database).insert_many(shifted.competitors)
    await CompetitorActivitiesRepository(database).insert_many(shifted.competitor_activities)
    await TrendsRepository(database).insert_many(shifted.trends)
    await InfluencersRepository(database).insert_many(shifted.influencers)
