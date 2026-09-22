from datetime import UTC, datetime, timedelta

import pytest

from app.intelligence.models import ActivityType, Channel
from app.pipelines.seed.loader import (
    SEED_AUTHORED_AT,
    SeedValidationError,
    load_seed_bundle,
    validate_seed_bundle,
)


def test_seed_bundle_meets_documented_minimums() -> None:
    coverage = validate_seed_bundle(load_seed_bundle(now=SEED_AUTHORED_AT), now=SEED_AUTHORED_AT)

    assert coverage.counts == {
        "companies": 1,
        "competitors": 3,
        "competitor_activities": 45,
        "trends": 16,
        "influencers": 20,
        "simulation_templates": 18,
    }
    assert set(coverage.activity_types) == {
        "NEW_BLOG",
        "SOCIAL_POST",
        "EXECUTIVE_POST",
        "NEW_PRODUCT",
        "PRODUCT_REMOVED",
        "PRICE_CHANGE",
        "PROMOTION",
        "CAMPAIGN_LAUNCH",
        "PAGE_UPDATE",
    }
    assert coverage.au_influencer_ratio >= 0.6


def test_seed_bundle_rebases_timestamps_at_load_time() -> None:
    future = datetime.now(UTC) + timedelta(days=90)
    authored_bundle = load_seed_bundle(now=SEED_AUTHORED_AT)
    rebased_bundle = load_seed_bundle(now=future)

    validate_seed_bundle(rebased_bundle, now=future)

    assert rebased_bundle.companies[0].updated_at == (
        authored_bundle.companies[0].updated_at + (future - SEED_AUTHORED_AT)
    )
    assert [item.detected_at for item in rebased_bundle.competitor_activities] == [
        item.detected_at + (future - SEED_AUTHORED_AT)
        for item in authored_bundle.competitor_activities
    ]


def test_seed_validation_rejects_missing_activity_coverage() -> None:
    bundle = load_seed_bundle()
    reduced = bundle.model_copy(update={"competitor_activities": bundle.competitor_activities[:2]})

    with pytest.raises(SeedValidationError, match="at least 45"):
        validate_seed_bundle(reduced)


def test_seed_validation_rejects_activity_older_than_30_days() -> None:
    bundle = load_seed_bundle(now=SEED_AUTHORED_AT)
    invalid_activity = bundle.competitor_activities[0].model_copy(
        update={"detected_at": SEED_AUTHORED_AT - timedelta(days=31)}
    )
    invalid_bundle = bundle.model_copy(
        update={"competitor_activities": [invalid_activity, *bundle.competitor_activities[1:]]}
    )

    with pytest.raises(SeedValidationError, match="last 30 days"):
        validate_seed_bundle(invalid_bundle, now=SEED_AUTHORED_AT)


def test_seed_validation_rejects_fewer_than_six_recent_activities() -> None:
    bundle = load_seed_bundle(now=SEED_AUTHORED_AT)
    recent_activity_ids = {
        item.id
        for item in bundle.competitor_activities
        if item.detected_at >= SEED_AUTHORED_AT - timedelta(hours=48)
    }
    invalid_bundle = bundle.model_copy(
        update={
            "competitor_activities": [
                item.model_copy(update={"detected_at": SEED_AUTHORED_AT - timedelta(hours=49)})
                if item.id in recent_activity_ids
                else item
                for item in bundle.competitor_activities
            ]
        }
    )

    with pytest.raises(SeedValidationError, match="latest 48 hours"):
        validate_seed_bundle(invalid_bundle, now=SEED_AUTHORED_AT)


def test_seed_validation_rejects_future_activity() -> None:
    bundle = load_seed_bundle(now=SEED_AUTHORED_AT)
    invalid_activity = bundle.competitor_activities[0].model_copy(
        update={"detected_at": SEED_AUTHORED_AT + timedelta(minutes=1)}
    )
    invalid_bundle = bundle.model_copy(
        update={"competitor_activities": [invalid_activity, *bundle.competitor_activities[1:]]}
    )

    with pytest.raises(SeedValidationError, match="future"):
        validate_seed_bundle(invalid_bundle, now=SEED_AUTHORED_AT)


def test_seed_load_rejects_naive_now() -> None:
    naive_now = datetime(2026, 9, 22)

    with pytest.raises(ValueError, match="timezone"):
        load_seed_bundle(now=naive_now)


def test_seed_validation_rejects_naive_now() -> None:
    naive_now = datetime(2026, 9, 22)

    with pytest.raises(ValueError, match="timezone"):
        validate_seed_bundle(load_seed_bundle(now=SEED_AUTHORED_AT), now=naive_now)


def test_seed_validation_rejects_record_without_is_mock() -> None:
    bundle = load_seed_bundle()
    invalid_company = bundle.companies[0].model_copy(update={"is_mock": False})
    invalid_bundle = bundle.model_copy(
        update={"companies": [invalid_company, *bundle.companies[1:]]}
    )

    with pytest.raises(SeedValidationError, match="is_mock=true"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_mock_activity_for_real_competitor() -> None:
    bundle = load_seed_bundle()
    invalid_activity = bundle.competitor_activities[0].model_copy(
        update={"competitor_id": "cpt_lyfe_marketing", "competitor_name": "Lyfe Marketing"}
    )
    invalid_bundle = bundle.model_copy(
        update={"competitor_activities": [invalid_activity, *bundle.competitor_activities[1:]]}
    )

    with pytest.raises(SeedValidationError, match="real competitors"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_restricted_activity_for_real_competitor() -> None:
    bundle = load_seed_bundle()
    restricted_activity = next(
        item
        for item in bundle.competitor_activities
        if item.activity_type == ActivityType.SOCIAL_POST
    )
    invalid_activity = restricted_activity.model_copy(
        update={
            "competitor_id": "cpt_lyfe_marketing",
            "competitor_name": "Lyfe Marketing",
            "is_simulated": True,
        }
    )
    invalid_bundle = bundle.model_copy(
        update={
            "competitor_activities": [
                invalid_activity if item.id == restricted_activity.id else item
                for item in bundle.competitor_activities
            ]
        }
    )

    with pytest.raises(SeedValidationError, match="must be fictional"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_fictional_competitor_website() -> None:
    bundle = load_seed_bundle()
    invalid_competitor = bundle.competitors[1].model_copy(
        update={"website": "https://brightlane.example.com"}
    )
    invalid_bundle = bundle.model_copy(
        update={"competitors": [bundle.competitors[0], invalid_competitor, *bundle.competitors[2:]]}
    )

    with pytest.raises(SeedValidationError, match="websites"):
        validate_seed_bundle(invalid_bundle)


@pytest.mark.parametrize(
    "url",
    [
        r"https://real-competitor.com\@brightlane.example/x",
        "https://[bad",
    ],
)
def test_seed_validation_rejects_unsafe_fictional_competitor_website(url: str) -> None:
    bundle = load_seed_bundle()
    invalid_competitor = bundle.competitors[1].model_copy(update={"website": url})
    invalid_bundle = bundle.model_copy(
        update={"competitors": [bundle.competitors[0], invalid_competitor, *bundle.competitors[2:]]}
    )

    with pytest.raises(SeedValidationError, match="websites"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_fictional_social_url() -> None:
    bundle = load_seed_bundle()
    invalid_competitor = bundle.competitors[1].model_copy(
        update={
            "social": {
                **bundle.competitors[1].social,
                Channel.LINKEDIN: "https://brightlane.example.com/linkedin",
            }
        }
    )
    invalid_bundle = bundle.model_copy(
        update={"competitors": [bundle.competitors[0], invalid_competitor, *bundle.competitors[2:]]}
    )

    with pytest.raises(SeedValidationError, match="social URLs"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_real_competitor_simulation_template() -> None:
    bundle = load_seed_bundle()
    invalid_template = bundle.simulation_templates[0].model_copy(
        update={"competitor_id": "cpt_lyfe_marketing"}
    )
    invalid_bundle = bundle.model_copy(
        update={"simulation_templates": [invalid_template, *bundle.simulation_templates[1:]]}
    )

    with pytest.raises(SeedValidationError, match="fictional seeded competitors"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_simulation_template_url() -> None:
    bundle = load_seed_bundle()
    invalid_template = bundle.simulation_templates[0].model_copy(
        update={"url": "https://example.com/not-a-demo-url"}
    )
    invalid_bundle = bundle.model_copy(
        update={"simulation_templates": [invalid_template, *bundle.simulation_templates[1:]]}
    )

    with pytest.raises(SeedValidationError, match="template URLs"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_example_com_fictional_activity_url() -> None:
    bundle = load_seed_bundle()
    invalid_activity = bundle.competitor_activities[0].model_copy(
        update={"url": "https://brightlane.example.com/not-a-demo-url"}
    )
    invalid_bundle = bundle.model_copy(
        update={"competitor_activities": [invalid_activity, *bundle.competitor_activities[1:]]}
    )

    with pytest.raises(SeedValidationError, match="activity URLs"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_trend_sample_post_url() -> None:
    bundle = load_seed_bundle()
    invalid_sample_post = (
        bundle.trends[0]
        .sample_posts[0]
        .model_copy(update={"url": "https://brightlane.example.com/post"})
    )
    invalid_trend = bundle.trends[0].model_copy(update={"sample_posts": [invalid_sample_post]})
    invalid_bundle = bundle.model_copy(update={"trends": [invalid_trend, *bundle.trends[1:]]})

    with pytest.raises(SeedValidationError, match="trend sample post URLs"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_influencer_profile_url() -> None:
    bundle = load_seed_bundle()
    invalid_influencer = bundle.influencers[0].model_copy(
        update={"profile_url": "https://influencers.example.com/aisha-patel"}
    )
    invalid_bundle = bundle.model_copy(
        update={"influencers": [invalid_influencer, *bundle.influencers[1:]]}
    )

    with pytest.raises(SeedValidationError, match="influencer URLs"):
        validate_seed_bundle(invalid_bundle)


def test_seed_validation_rejects_non_example_influencer_evidence_url() -> None:
    bundle = load_seed_bundle()
    invalid_evidence = (
        bundle.influencers[0]
        .evidence[0]
        .model_copy(update={"url": "https://influencers.example.com/aisha-patel/notes"})
    )
    invalid_influencer = bundle.influencers[0].model_copy(
        update={"evidence": [invalid_evidence, *bundle.influencers[0].evidence[1:]]}
    )
    invalid_bundle = bundle.model_copy(
        update={"influencers": [invalid_influencer, *bundle.influencers[1:]]}
    )

    with pytest.raises(SeedValidationError, match="influencer URLs"):
        validate_seed_bundle(invalid_bundle)
