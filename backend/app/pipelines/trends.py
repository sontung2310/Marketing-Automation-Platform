"""Aggregate Pace AI posts into dated, owned trend records."""

from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import (
    Channel,
    Provenance,
    SamplePost,
    SourceSystem,
    Trend,
    TrendDirection,
)
from app.intelligence.repositories.base import Document, UpsertResult
from app.intelligence.repositories.trends import TrendsRepository
from app.pipelines.sources.pace import PacePost, PaceReadResult

logger = logging.getLogger(__name__)

PACE_POST_THRESHOLD = 50
PACE_SOURCE_CHANNELS: Mapping[str, Channel] = {
    "bbc_rss": Channel.NEWS,
    "duckduckgo_web": Channel.WEBSITE,
    "guardian_api": Channel.NEWS,
    "news_rss": Channel.NEWS,
    "newsapi": Channel.NEWS,
    "reddit_playwright": Channel.REDDIT,
    "techcrunch_rss": Channel.NEWS,
    "x_playwright": Channel.X,
    "youtube_search": Channel.YOUTUBE,
}
PACE_SENTIMENT_LABELS: Mapping[str, int] = {"positive": 1, "negative": -1, "neutral": 0}


class PaceReader(Protocol):
    async def read(self, *, window_start: datetime, window_end: datetime) -> PaceReadResult: ...


@dataclass(frozen=True)
class TrendAggregationResult:
    trends: list[Trend]
    skipped: int = 0


@dataclass(frozen=True)
class TrendPipelineSummary:
    trends: PipelineCounts
    used_seed_fallback: bool
    window_end_date: date


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


def utc_window_end(window_end_date: date) -> datetime:
    return datetime.combine(window_end_date, time.min, tzinfo=UTC)


def _signed_sentiment(post: PacePost) -> float:
    sentiment = post.sentiment
    if sentiment is None:
        logger.warning(
            "Pace post has missing or unknown sentiment",
            extra={"ctx": {"source_id": post.source_id}},
        )
        return 0.0
    label = sentiment.label
    if label not in PACE_SENTIMENT_LABELS:
        logger.warning(
            "Pace post has missing or unknown sentiment",
            extra={"ctx": {"source_id": post.source_id}},
        )
        return 0.0
    assert label is not None
    score = sentiment.score
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        logger.warning(
            "Pace post has invalid sentiment score",
            extra={"ctx": {"source_id": post.source_id}},
        )
        return 0.0
    return PACE_SENTIMENT_LABELS[label] * min(1.0, max(0.0, float(score)))


def _keyword_values(posts: Iterable[PacePost]) -> list[str]:
    scores: dict[str, list[float]] = defaultdict(list)
    for post in posts:
        for keyword in post.keywords:
            if not keyword.term or not keyword.term.strip():
                continue
            if isinstance(keyword.score, bool) or not isinstance(keyword.score, (int, float)):
                continue
            scores[keyword.term.strip()].append(float(keyword.score))
    ranked = sorted(
        ((term, sum(values) / len(values)) for term, values in scores.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [term for term, _ in ranked[:5]]


def _source_ref(window_end_date: date, channel: Channel, topic: str) -> str:
    digest = hashlib.sha256(topic.encode("utf-8")).hexdigest()
    return f"trend:{window_end_date.isoformat()}:{channel.value}:{digest}"


def _trend_id(source_ref: str) -> str:
    digest = hashlib.sha256(source_ref.encode("utf-8")).hexdigest()
    return f"trd_{digest}"


def aggregate_trends(
    posts: Sequence[PacePost],
    *,
    company_id: str,
    window_end_date: date,
    computed_at: datetime | None = None,
) -> TrendAggregationResult:
    """Build trend models from one captured 14-day Pace window."""

    window_end = utc_window_end(window_end_date)
    current_start = window_end - timedelta(days=7)
    previous_start = window_end - timedelta(days=14)
    groups: dict[tuple[str, Channel], list[PacePost]] = defaultdict(list)
    skipped = 0
    for post in posts:
        channel = PACE_SOURCE_CHANNELS.get(post.source)
        if channel is None:
            skipped += 1
            logger.warning(
                "Skipping Pace post with unknown source %s",
                post.source_id,
                extra={"ctx": {"source_id": post.source_id, "source": post.source}},
            )
            continue
        for topic in post.topics:
            normalized_topic = topic.strip()
            if normalized_topic:
                groups[(normalized_topic, channel)].append(post)

    trends: list[Trend] = []
    calculated_at = computed_at or datetime.now(UTC)
    if calculated_at.tzinfo is None:
        calculated_at = calculated_at.replace(tzinfo=UTC)
    else:
        calculated_at = calculated_at.astimezone(UTC)
    for (topic, channel), grouped_posts in sorted(groups.items(), key=lambda item: item[0]):
        current_posts = [
            post for post in grouped_posts if current_start <= post.created_at < window_end
        ]
        previous_posts = [
            post for post in grouped_posts if previous_start <= post.created_at < current_start
        ]
        previous_count = len(previous_posts)
        momentum = (len(current_posts) - previous_count) / max(previous_count, 1) * 100
        if momentum > 10:
            direction = TrendDirection.RISING
        elif momentum < -10:
            direction = TrendDirection.FALLING
        else:
            direction = TrendDirection.STEADY
        ordered_posts = sorted(
            grouped_posts,
            key=lambda post: (-post.created_at.timestamp(), post.source_id),
        )
        sample_posts = [
            SamplePost(title=post.title, url=post.url, channel=channel)
            for post in ordered_posts[:3]
        ]
        source_ref = _source_ref(window_end_date, channel, topic)
        trends.append(
            Trend(
                id=_trend_id(source_ref),
                company_id=company_id,
                topic=topic,
                keywords=_keyword_values(grouped_posts),
                channel=channel,
                window_days=7,
                mention_count=len(current_posts),
                momentum_pct=momentum,
                direction=direction,
                sentiment=sum(_signed_sentiment(post) for post in grouped_posts)
                / len(grouped_posts),
                sample_posts=sample_posts,
                computed_at=calculated_at,
                source=Provenance(system=SourceSystem.PACE, ref_id=source_ref),
                is_mock=False,
            )
        )
    return TrendAggregationResult(trends=trends, skipped=skipped)


def _known_source_posts(posts: Iterable[PacePost]) -> tuple[list[PacePost], int]:
    known: list[PacePost] = []
    skipped = 0
    for post in posts:
        if post.source not in PACE_SOURCE_CHANNELS:
            skipped += 1
            logger.warning(
                "Skipping Pace post with unknown source %s",
                post.source_id,
                extra={"ctx": {"source_id": post.source_id, "source": post.source}},
            )
            continue
        if not any(topic.strip() for topic in post.topics):
            skipped += 1
            logger.warning(
                "Skipping Pace post with no usable topics",
                extra={"ctx": {"source_id": post.source_id}},
            )
            continue
        known.append(post)
    return known, skipped


async def run_trend_pipeline(
    reader: PaceReader,
    database: AsyncDatabase[Document],
    *,
    company_id: str = "cmp_marketing_eye",
    window_end_date: date | None = None,
) -> TrendPipelineSummary:
    """Aggregate a live Pace window, preserving seeded trends below threshold."""

    captured_end_date = window_end_date or datetime.now(UTC).date()
    window_end = utc_window_end(captured_end_date)
    source_result = await reader.read(
        window_start=window_end - timedelta(days=14), window_end=window_end
    )
    known_posts, unknown_skipped = _known_source_posts(source_result.posts)
    if len(known_posts) < PACE_POST_THRESHOLD:
        return TrendPipelineSummary(
            trends=PipelineCounts(skipped=source_result.skipped + unknown_skipped),
            used_seed_fallback=True,
            window_end_date=captured_end_date,
        )
    aggregation = aggregate_trends(
        known_posts,
        company_id=company_id,
        window_end_date=captured_end_date,
        computed_at=window_end,
    )
    repository = TrendsRepository(database)
    counts = PipelineCounts(skipped=source_result.skipped + unknown_skipped + aggregation.skipped)
    for trend in aggregation.trends:
        counts = counts.add(await repository.upsert_by_source(trend))
    return TrendPipelineSummary(
        trends=counts,
        used_seed_fallback=False,
        window_end_date=captured_end_date,
    )
