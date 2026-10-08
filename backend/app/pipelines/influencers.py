"""Normalize DCT influencer candidates into the owned influencers collection."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol

from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Channel, EvidenceLink, Influencer, Provenance, SourceSystem
from app.intelligence.repositories.base import Document, UpsertResult
from app.intelligence.repositories.influencers import InfluencersRepository
from app.pipelines.sources.dct import DctCandidate, DctReadResult

logger = logging.getLogger(__name__)

DCT_PLATFORM_CHANNELS: Mapping[str, Channel] = {"x": Channel.X}


class DctReader(Protocol):
    async def read(self) -> DctReadResult: ...


@dataclass(frozen=True)
class InfluencerPipelineSummary:
    influencers: PipelineCounts


@dataclass(frozen=True)
class PipelineCounts:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.skipped

    def add(self, result: UpsertResult) -> PipelineCounts:
        return replace(
            self,
            inserted=self.inserted + int(result.inserted),
            updated=self.updated + int(result.updated),
            skipped=self.skipped + int(result.skipped),
        )


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _engagement_rate(candidate: DctCandidate) -> float:
    followers = _numeric(candidate.followers)
    if followers is None or followers <= 0:
        return 0.0
    rates: list[float] = []
    for post in candidate.recent_posts:
        likes = _numeric(post.likes)
        replies = _numeric(post.replies)
        reposts = _numeric(post.reposts)
        if likes is None or replies is None or reposts is None:
            continue
        rates.append(max(0.0, (likes + replies + reposts) / followers))
    if not rates:
        return 0.0
    return min(1.0, sum(rates) / len(rates))


def _evidence(candidate: DctCandidate) -> list[EvidenceLink]:
    evidence: list[EvidenceLink] = []
    for post in candidate.recent_posts:
        text = post.text.strip() if post.text else ""
        url = post.url.strip() if post.url else ""
        if not text or not url:
            continue
        evidence.append(EvidenceLink(title=text, url=url))
        if len(evidence) == 3:
            break
    return evidence


def build_owned_influencer(candidate: DctCandidate, *, company_id: str) -> Influencer | None:
    channel = DCT_PLATFORM_CHANNELS.get(candidate.platform)
    if channel is None:
        logger.warning(
            "Skipping DCT candidate with unknown platform %s",
            candidate.source_id,
            extra={"ctx": {"source_id": candidate.source_id, "platform": candidate.platform}},
        )
        return None
    followers = _numeric(candidate.followers)
    if followers is None or followers < 0:
        raise ValueError("candidate followers must be a non-negative number")
    handle = candidate.handle.strip()
    if not handle.startswith("@"):
        handle = f"@{handle}"
    relevance_score = min(1.0, max(0.0, float(candidate.latest_final_score) / 100.0))
    return Influencer(
        id=f"inf_{candidate.source_id}",
        company_id=company_id,
        name=candidate.display_name.strip(),
        handle=handle,
        channel=channel,
        profile_url=candidate.profile_url.strip(),
        avatar_url=candidate.avatar_url,
        followers=int(followers),
        engagement_rate=_engagement_rate(candidate),
        topics=[],
        audience_region="UNKNOWN",
        relevance_score=relevance_score,
        evidence=_evidence(candidate),
        source=Provenance(system=SourceSystem.DCT, ref_id=candidate.source_id),
        is_mock=False,
    )


async def run_influencer_pipeline(
    reader: DctReader,
    database: AsyncDatabase[Document],
    *,
    company_id: str = "cmp_marketing_eye",
) -> InfluencerPipelineSummary:
    """Read DCT candidates and idempotently write owned influencer records."""

    source_result = await reader.read()
    repository = InfluencersRepository(database)
    counts = PipelineCounts(skipped=source_result.skipped)
    for candidate in source_result.candidates:
        try:
            influencer = build_owned_influencer(candidate, company_id=company_id)
            if influencer is None:
                counts = replace(counts, skipped=counts.skipped + 1)
                continue
            counts = counts.add(await repository.upsert_by_source(influencer))
        except (TypeError, ValueError) as error:
            counts = replace(counts, skipped=counts.skipped + 1)
            logger.warning(
                "Skipping DCT candidate %s: %s",
                candidate.source_id,
                error,
                extra={"ctx": {"source_id": candidate.source_id}},
            )
    # Only the current top candidates stay; an empty read keeps the last good set.
    if source_result.candidates:
        deleted = await repository.delete_by_source_except(
            company_id, SourceSystem.DCT, {c.source_id for c in source_result.candidates}
        )
        counts = replace(counts, deleted=deleted)
    return InfluencerPipelineSummary(influencers=counts)
