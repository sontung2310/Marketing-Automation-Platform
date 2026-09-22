from typing import cast

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.intelligence.models import Channel, SourceSystem
from app.intelligence.repositories.base import Document
from app.pipelines.influencers import DCT_PLATFORM_CHANNELS, build_owned_influencer
from app.pipelines.sources.dct import DctCandidate, DctSource, SourcePost


def candidate(**overrides: object) -> DctCandidate:
    values: dict[str, object] = {
        "source_id": "candidate-1",
        "platform": "x",
        "display_name": "A Creator",
        "handle": "creator",
        "profile_url": "https://x.example/creator",
        "followers": 1000,
        "latest_final_score": 50,
        "recent_posts": [
            SourcePost(text="One", url="https://x.example/1", likes=10, replies=5, reposts=5),
            SourcePost(text="Two", url="https://x.example/2", likes=20, replies=10, reposts=0),
        ],
    }
    values.update(overrides)
    return DctCandidate.model_validate(values)


def test_dct_registry_maps_every_documented_platform() -> None:
    assert DCT_PLATFORM_CHANNELS == {"x": Channel.X}


def test_build_owned_influencer_maps_and_bounds_fields() -> None:
    influencer = build_owned_influencer(candidate(), company_id="cmp_marketing_eye")

    assert influencer is not None
    assert influencer.id == "inf_candidate-1"
    assert influencer.handle == "@creator"
    assert influencer.channel is Channel.X
    assert influencer.engagement_rate == pytest.approx(0.025)
    assert influencer.relevance_score == 0.5
    assert influencer.topics == []
    assert influencer.audience_region == "UNKNOWN"
    assert len(influencer.evidence) == 2
    assert influencer.source.system is SourceSystem.DCT


def test_unknown_platform_is_skipped() -> None:
    assert (
        build_owned_influencer(candidate(platform="mastodon"), company_id="cmp_marketing_eye")
        is None
    )


def test_engagement_and_evidence_handle_missing_metrics() -> None:
    influencer = build_owned_influencer(
        candidate(
            followers=0,
            recent_posts=[SourcePost(text="No URL")],
            latest_final_score=500,
        ),
        company_id="cmp_marketing_eye",
    )

    assert influencer is not None
    assert influencer.engagement_rate == 0.0
    assert influencer.relevance_score == 1.0
    assert influencer.evidence == []


class _Cursor:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def sort(self, _ordering: list[tuple[str, int]]) -> "_Cursor":
        return self

    def limit(self, limit: int) -> "_Cursor":
        self.documents = self.documents[:limit]
        return self

    def __aiter__(self) -> "_Cursor":
        self.index = 0
        return self

    async def __anext__(self) -> Document:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return document


class _Collection:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.query: Document | None = None

    def find(self, query: Document) -> _Cursor:
        self.query = query
        return _Cursor(self.documents)


class _Database:
    def __init__(self, documents: list[Document]) -> None:
        self.collection = _Collection(documents)

    def __getitem__(self, name: str) -> _Collection:
        assert name == "influencer_candidates"
        return self.collection


@pytest.mark.asyncio
async def test_dct_source_is_bounded_and_skips_malformed_documents() -> None:
    database = _Database(
        [
            {
                "_id": "candidate-1",
                "platform": "x",
                "profile": {"display_name": "Creator", "followers": 10},
                "account": {"handle": "creator", "profile_url": "https://x.example/creator"},
                "evaluation": {"latest_final_score": 50, "score_breakdown": {}},
                "platform_data": {"recent_posts": []},
            },
            {"_id": "malformed", "platform": "x"},
        ]
    )

    result = await DctSource(cast(AsyncDatabase[Document], database)).read()

    assert len(result.candidates) == 1
    assert result.skipped == 1
    assert database.collection.query == {
        "company_id": "marketingeye.com.au",
        "evaluation.status": "eligible",
        "evaluation.latest_final_score": {"$type": "number"},
    }
