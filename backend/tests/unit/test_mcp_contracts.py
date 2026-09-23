"""Pure tests for the MCP boundary contracts and projections."""

import logging
from datetime import UTC, datetime

import pytest

from app.core.errors import UpstreamUnavailableError
from app.intelligence.models import (
    ActivitySummary,
    ActivitySummaryCount,
    ActivitySummaryRecent,
    ActivityType,
    Channel,
    Competitor,
    CompetitorActivity,
    Provenance,
    SourceSystem,
)
from app.mcp_server.contracts import (
    ActivitySearchArguments,
    CompactCompetitor,
    ToolErrorEnvelope,
    capped_limit,
    compact_activity,
    compact_activity_summary,
    compact_competitor,
    parse_tool_arguments,
)
from app.mcp_server.server import _results_or_note, _tool_boundary


@pytest.mark.parametrize("value, expected", [(10, 10), (25, 25), (500, 25)])
def test_capped_limit(value: int, expected: int) -> None:
    assert capped_limit(value) == expected


def test_parse_tool_arguments_returns_validation_envelope() -> None:
    parsed = parse_tool_arguments(ActivitySearchArguments, {"activity_types": ["BOGUS"]})

    assert isinstance(parsed, ToolErrorEnvelope)
    assert parsed.error.code == "VALIDATION_ERROR"


def test_results_or_note_adds_note_only_for_empty_results() -> None:
    competitor = CompactCompetitor(
        id="cpt_brightlane",
        name="Brightlane",
        website="https://brightlane.example",
        is_fictional=True,
        channels=[Channel.LINKEDIN],
    )

    populated = _results_or_note([competitor])
    empty = _results_or_note([])

    assert populated.results == [competitor]
    assert populated.note is None
    assert empty.results == []
    assert empty.note == "No records matched the request."


def test_compact_projections_keep_the_documented_fields() -> None:
    now = datetime.now(UTC)
    activity = _activity(now)
    competitor = Competitor(
        _id="cpt_brightlane",
        company_id="cmp_marketing_eye",
        name="Brightlane",
        website="https://brightlane.example",
        is_fictional=True,
        social={Channel.LINKEDIN: "https://linkedin.example/brightlane", Channel.X: None},
        source=_source("competitor"),
        is_mock=True,
    )
    summary = ActivitySummary(
        counts=[
            ActivitySummaryCount(
                competitor_id=competitor.id,
                competitor_name=competitor.name,
                activity_type=ActivityType.SOCIAL_POST,
                count=1,
            )
        ],
        recent_items=[
            ActivitySummaryRecent(
                competitor_id=competitor.id,
                competitor_name=competitor.name,
                items=[activity],
            )
        ],
    )

    compact_competitor_result = compact_competitor(competitor)
    compact_activity_result = compact_activity(activity)
    compact_summary_result = compact_activity_summary(summary)

    assert set(compact_competitor_result.model_dump()) == {
        "id",
        "name",
        "website",
        "is_fictional",
        "channels",
    }
    assert compact_competitor_result.channels == [Channel.LINKEDIN]
    assert set(compact_activity_result.model_dump()) == {
        "id",
        "competitor_name",
        "activity_type",
        "channel",
        "title",
        "summary",
        "url",
        "detected_at",
        "is_mock",
        "is_simulated",
    }
    assert set(compact_summary_result.recent_items[0].items[0].model_dump()) == set(
        compact_activity_result.model_dump()
    )
    assert "note" not in compact_summary_result.model_dump()


@pytest.mark.asyncio
async def test_tool_boundary_maps_repository_failure_and_logs_tool_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingRepository:
        async def read(self) -> None:
            raise UpstreamUnavailableError("database unavailable")

    repository = FailingRepository()

    @_tool_boundary("stub_tool")
    async def handler() -> None:
        await repository.read()

    with caplog.at_level(logging.ERROR, logger="app.mcp_server.server"):
        result = await handler()

    assert isinstance(result, ToolErrorEnvelope)
    assert result.error.code == "UPSTREAM_UNAVAILABLE"
    assert "stub_tool" in caplog.text


def _activity(now: datetime) -> CompetitorActivity:
    return CompetitorActivity(
        _id="act_social_001",
        company_id="cmp_marketing_eye",
        competitor_id="cpt_brightlane",
        competitor_name="Brightlane",
        activity_type=ActivityType.SOCIAL_POST,
        channel=Channel.LINKEDIN,
        title="A social post",
        summary="A compact test activity.",
        url="https://brightlane.example/post",
        occurred_at=now,
        detected_at=now,
        source=_source("activity"),
        is_mock=True,
        is_simulated=False,
        ingested_at=now,
    )


def _source(ref_id: str) -> Provenance:
    return Provenance(system=SourceSystem.MOCK_SEED, ref_id=ref_id)
