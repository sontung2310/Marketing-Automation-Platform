from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.intelligence.models import (
    ActivityType,
    BrandVoice,
    Channel,
    Company,
    CompetitorActivity,
    Provenance,
    SourceSystem,
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
        channels=[Channel.LINKEDIN],
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
            activity_type=ActivityType.SOCIAL_POST,
            channel=Channel.LINKEDIN,
            title="A title",
            summary="A summary",
            occurred_at=datetime(2026, 9, 22, tzinfo=UTC),
            detected_at=datetime(2026, 9, 22, tzinfo=UTC),
            source=Provenance(system=SourceSystem.MOCK_SEED, ref_id="activity-2"),
            is_mock=True,
            is_simulated=False,
            ingested_at=datetime(2026, 9, 22, tzinfo=UTC),
        )
