from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.intelligence.models import (
    ActivityType,
    BrandVoice,
    Channel,
    Company,
    CompetitorActivity,
    Influencer,
    Provenance,
    SourceSystem,
    Trend,
    normalize_keywords,
)


def _company() -> Company:
    return Company(
        _id="cmp_marketing_eye",
        name="Marketing Eye",
        website="https://www.marketingeye.com.au",
        industry="B2B marketing agency",
        region="AU",
        summary="Useful B2B marketing.",
        icp=[{"segment": "SaaS", "pains": ["Noise"], "goals": ["Growth"]}],
        positioning="Clear B2B growth.",
        services=[{"name": "Strategy", "description": "Positioning.", "price_from": 1}],
        brand_voice=BrandVoice(
            tone=["clear"], do=["help"], dont=["hype"], sample_copy=["Be useful."]
        ),
        spokesperson={"name": "Sam Lee", "role": "CEO", "voice_notes": ["Lead with insight."]},
        channels=[Channel.LINKEDIN],
        tracked_keywords=["AI search"],
        content_pillars=["Growth"],
        is_mock=True,
        updated_at=datetime(2026, 9, 22, tzinfo=UTC),
    )


def test_company_round_trips_mongo_id_alias() -> None:
    company = _company()

    assert company.id == "cmp_marketing_eye"
    assert company.model_dump(by_alias=True)["_id"] == "cmp_marketing_eye"


@pytest.mark.parametrize("bad_id", ["marketing_eye", "cmp_"])
def test_company_rejects_malformed_prefixed_id(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        payload = _company().model_dump(by_alias=True)
        payload["_id"] = bad_id
        Company.model_validate(payload)


def test_company_requires_a_spokesperson() -> None:
    payload = _company().model_dump(by_alias=True)
    del payload["spokesperson"]

    with pytest.raises(ValidationError, match="spokesperson"):
        Company.model_validate(payload)


def test_activity_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        CompetitorActivity(
            _id="act_seed_001",
            company_id="cmp_marketing_eye",
            competitor_id="cpt_lyfe_marketing",
            competitor_name="Lyfe Marketing",
            activity_type=ActivityType.NEW_BLOG,
            channel=Channel.WEBSITE,
            title="A title",
            summary="A summary",
            occurred_at=datetime(2026, 9, 22),
            detected_at=datetime(2026, 9, 22, tzinfo=UTC),
            source=Provenance(system=SourceSystem.MOCK_SEED, ref_id="activity-1"),
            is_mock=True,
            is_simulated=False,
            ingested_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_activity_rejects_incompatible_type_fields() -> None:
    with pytest.raises(ValidationError, match="engagement"):
        CompetitorActivity(
            _id="act_seed_002",
            company_id="cmp_marketing_eye",
            competitor_id="cpt_brightlane",
            competitor_name="Brightlane Marketing",
            activity_type=ActivityType.NEW_BLOG,
            channel=Channel.WEBSITE,
            title="A title",
            summary="A summary",
            engagement={"likes": 1, "comments": 0, "shares": 0},
            occurred_at=datetime(2026, 9, 22, tzinfo=UTC),
            detected_at=datetime(2026, 9, 22, tzinfo=UTC),
            source=Provenance(system=SourceSystem.MOCK_SEED, ref_id="activity-2"),
            is_mock=True,
            is_simulated=False,
            ingested_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_source_derived_collections_allow_empty_optional_lists() -> None:
    influencer = Influencer(
        id="inf_dct_1",
        company_id="cmp_marketing_eye",
        name="Creator",
        handle="@creator",
        channel=Channel.X,
        profile_url="https://x.example/creator",
        followers=1,
        engagement_rate=0.0,
        topics=[],
        audience_region="UNKNOWN",
        relevance_score=0.5,
        evidence=[],
        source=Provenance(system=SourceSystem.DCT, ref_id="dct-1"),
        is_mock=False,
    )
    trend = Trend(
        id="trd_pace_1",
        company_id="cmp_marketing_eye",
        topic="Marketing",
        keywords=[],
        channel=Channel.X,
        window_days=7,
        mention_count=0,
        momentum_pct=0.0,
        direction="STEADY",
        sentiment=0.0,
        sample_posts=[{"title": "A post", "url": "https://example.test/post", "channel": "X"}],
        computed_at=datetime(2026, 9, 22, tzinfo=UTC),
        source=Provenance(system=SourceSystem.PACE, ref_id="pace-1"),
        is_mock=False,
    )

    assert influencer.topics == []
    assert influencer.evidence == []
    assert trend.keywords == []


def test_tracked_keywords_trim_dedupe_and_reject_blanks() -> None:
    assert normalize_keywords([" AI search ", "ai search", "SEO"]) == ["AI search", "SEO"]
    with pytest.raises(ValueError):
        normalize_keywords(["SEO", "  "])
