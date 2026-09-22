from datetime import UTC, datetime
from typing import cast

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import ActivityType, Channel
from app.intelligence.repositories.base import Document
from app.pipelines.competitor_activity import (
    activity_type_for_change,
    build_owned_activity,
    title_for_change,
)
from app.pipelines.sources.competitorscope import (
    CompetitorScopeActivity,
    CompetitorScopeSource,
    SourceChange,
    SourceCompetitor,
    SourceMonitoringTarget,
)


class FakeCursor:
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.documents = documents

    def __aiter__(self) -> "FakeCursor":
        self._index = 0
        return self

    async def __anext__(self) -> dict[str, object]:
        if self._index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self._index]
        self._index += 1
        return document


class FakeCollection:
    def __init__(self, documents: list[dict[str, object]]) -> None:
        self.documents = documents

    def find(self, _query: dict[str, object]) -> FakeCursor:
        return FakeCursor(self.documents)


class FakeDatabase:
    def __init__(self, collections: dict[str, list[dict[str, object]]]) -> None:
        self.collections = {
            name: FakeCollection(documents) for name, documents in collections.items()
        }

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections[name]


def source_activity(
    *,
    change_type: str | None = "NEW_BLOG",
    narrative_summary: str | None = "New article published",
    detected_url: str | None = "https://lyfemarketing.com/blog/new",
    target_url: str | None = "https://lyfemarketing.com/blog",
) -> CompetitorScopeActivity:
    return CompetitorScopeActivity(
        change=SourceChange(
            _id="change-1",
            monitoring_target_id="target-1",
            change_type=change_type,
            summary="4 lines added",
            narrative_summary=narrative_summary,
            detected_url=detected_url,
            detected_at=datetime(2026, 9, 22, tzinfo=UTC),
            is_simulated=True,
        ),
        competitor=SourceCompetitor(
            _id="competitor-1",
            name="Lyfe Marketing",
            website_url="https://www.lyfemarketing.com/",
            company_id="source-company-1",
        ),
        target=SourceMonitoringTarget(
            _id="target-1",
            competitor_id="competitor-1",
            url=target_url,
        ),
    )


@pytest.mark.parametrize(
    ("change_type", "expected"),
    [
        ("NEW_BLOG", ActivityType.NEW_BLOG),
        ("NEW_PRODUCT", ActivityType.NEW_PRODUCT),
        ("PRICE_CHANGE", ActivityType.PRICE_CHANGE),
        ("PRODUCT_REMOVED", ActivityType.PRODUCT_REMOVED),
    ],
)
def test_supported_change_types_are_mapped(change_type: str, expected: ActivityType) -> None:
    assert activity_type_for_change(change_type) == expected


def test_unknown_change_type_is_skipped() -> None:
    activity = source_activity(change_type="FUTURE_CHANGE")

    assert activity_type_for_change(activity.change.change_type) is None
    assert (
        build_owned_activity(activity, company_id="cmp_marketing_eye", competitor_id="cpt_1")
        is None
    )


def test_title_uses_url_fallback_and_truncates_unicode_code_points() -> None:
    activity = source_activity(narrative_summary="", detected_url="", target_url="é" * 130)

    title = title_for_change(activity)

    assert len(title) == 120
    assert title.startswith("NEW_BLOG detected at ")
    assert title.endswith("...")


def test_activity_preserves_source_fields() -> None:
    owned = build_owned_activity(
        source_activity(), company_id="cmp_marketing_eye", competitor_id="cpt_competitor-1"
    )

    assert owned is not None
    assert owned.activity_type is ActivityType.NEW_BLOG
    assert owned.channel is Channel.WEBSITE
    assert owned.source.ref_id == "change-1"
    assert owned.occurred_at == owned.detected_at
    assert owned.is_mock is False
    assert owned.is_simulated is True


@pytest.mark.asyncio
async def test_source_join_excludes_unscoped_and_missing_target_changes(
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_company_id = "507f1f77bcf86cd799439011"
    eligible_competitor_id = "507f1f77bcf86cd799439012"
    unscoped_competitor_id = "507f1f77bcf86cd799439013"
    target_id = "507f1f77bcf86cd799439014"
    source_database = FakeDatabase(
        {
            "companies": [{"_id": source_company_id, "name": "Marketing Eye"}],
            "competitors": [
                {
                    "_id": eligible_competitor_id,
                    "name": "Lyfe Marketing",
                    "website_url": "https://www.lyfemarketing.com/",
                    "company_id": source_company_id,
                },
                {
                    "_id": unscoped_competitor_id,
                    "name": "Brown Bag Marketing",
                    "website_url": "https://brownbagmarketing.com/",
                },
            ],
            "monitoring_targets": [
                {
                    "_id": target_id,
                    "competitor_id": eligible_competitor_id,
                    "url": "https://www.lyfemarketing.com/blog",
                },
            ],
            "changes": [
                {
                    "_id": "507f1f77bcf86cd799439015",
                    "monitoring_target_id": target_id,
                    "change_type": "NEW_BLOG",
                    "summary": "new blog",
                    "narrative_summary": "New blog",
                    "detected_at": datetime(2026, 9, 22, tzinfo=UTC),
                },
                {
                    "_id": "507f1f77bcf86cd799439016",
                    "monitoring_target_id": "507f1f77bcf86cd799439099",
                    "change_type": "NEW_BLOG",
                    "summary": "missing target",
                    "detected_at": datetime(2026, 9, 22, tzinfo=UTC),
                },
            ],
        }
    )

    with caplog.at_level("WARNING"):
        result = await CompetitorScopeSource(cast(AsyncDatabase[Document], source_database)).read()

    assert len(result.activities) == 1
    assert result.activities[0].competitor.name == "Lyfe Marketing"
    assert result.skipped == 1
    assert "507f1f77bcf86cd799439016" in caplog.text
