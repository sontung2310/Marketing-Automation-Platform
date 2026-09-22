from datetime import UTC, datetime, timedelta

import pytest

from app.intelligence.models import ActivityType
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
