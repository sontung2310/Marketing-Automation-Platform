from datetime import UTC, date, datetime, timedelta

import pytest

from app.intelligence.models import Channel, TrendDirection
from app.pipelines.sources.pace import PaceKeyword, PacePost, PaceReadResult, PaceSentiment
from app.pipelines.trends import (
    PACE_SENTIMENT_LABELS,
    PACE_SOURCE_CHANNELS,
    aggregate_trends,
    run_trend_pipeline,
)


def post(
    source_id: str,
    created_at: datetime,
    *,
    source: str = "x_playwright",
    topics: list[str] | None = None,
    sentiment: PaceSentiment | None = None,
) -> PacePost:
    return PacePost(
        source_id=source_id,
        created_at=created_at,
        topics=topics if topics is not None else ["Marketing"],
        keywords=[PaceKeyword(term="growth", score=0.8)],
        source=source,
        title=f"Title {source_id}",
        url=f"https://example.test/{source_id}",
        sentiment=sentiment,
    )


def test_pace_registries_cover_documented_values() -> None:
    assert set(PACE_SOURCE_CHANNELS) == {
        "bbc_rss",
        "duckduckgo_web",
        "guardian_api",
        "news_rss",
        "newsapi",
        "reddit_playwright",
        "techcrunch_rss",
        "x_playwright",
        "youtube_search",
    }
    assert PACE_SOURCE_CHANNELS["x_playwright"] is Channel.X
    assert PACE_SENTIMENT_LABELS == {"positive": 1, "negative": -1, "neutral": 0}


def test_aggregate_computes_momentum_sentiment_keywords_and_tied_samples() -> None:
    window_end = date(2026, 9, 22)
    posts = [
        post(
            "b",
            datetime(2026, 9, 20, tzinfo=UTC),
            sentiment=PaceSentiment(label="positive", score=0.8),
        ),
        post(
            "a",
            datetime(2026, 9, 20, tzinfo=UTC),
            sentiment=PaceSentiment(label="negative", score=0.2),
        ),
        post(
            "c",
            datetime(2026, 9, 10, tzinfo=UTC),
            sentiment=PaceSentiment(label="neutral", score=0.9),
        ),
    ]

    result = aggregate_trends(posts, company_id="cmp_marketing_eye", window_end_date=window_end)

    assert result.skipped == 0
    trend = result.trends[0]
    assert trend.channel is Channel.X
    assert trend.mention_count == 2
    assert trend.momentum_pct == pytest.approx(100.0)
    assert trend.direction is TrendDirection.RISING
    assert trend.sentiment == pytest.approx(0.2)
    assert trend.keywords == ["growth"]
    assert [sample.title for sample in trend.sample_posts] == ["Title a", "Title b", "Title c"]
    assert trend.source.ref_id.startswith("trend:2026-09-22:X:")


@pytest.mark.asyncio
async def test_unknown_source_is_skipped_and_fallback_performs_no_writes() -> None:
    class Reader:
        async def read(self, *, window_start: datetime, window_end: datetime):
            return PaceReadResult(
                posts=[post("unknown", window_end - timedelta(days=1), source="other")],
                skipped=0,
            )

    class Database:
        def __getitem__(self, _name: str):
            raise AssertionError("fallback must not access an owned collection")

    result = await run_trend_pipeline(Reader(), Database(), window_end_date=date(2026, 9, 22))

    assert result.used_seed_fallback is True
    assert result.trends.inserted == 0
    assert result.trends.updated == 0
    assert result.trends.skipped == 1


@pytest.mark.asyncio
async def test_posts_without_topics_do_not_cross_live_threshold() -> None:
    class Reader:
        async def read(self, *, window_start: datetime, window_end: datetime) -> PaceReadResult:
            return PaceReadResult(
                posts=[
                    post(
                        str(index),
                        window_end - timedelta(days=1),
                        topics=[],
                    )
                    for index in range(50)
                ]
            )

    class Database:
        def __getitem__(self, _name: str):
            raise AssertionError("topic-less posts must not write live trends")

    result = await run_trend_pipeline(Reader(), Database(), window_end_date=date(2026, 9, 22))

    assert result.used_seed_fallback is True
    assert result.trends.inserted == 0
    assert result.trends.skipped == 50
