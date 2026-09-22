from datetime import UTC, datetime

import pytest

from app.pipelines.seed.loader import SeedValidationError, load_seed_bundle, validate_seed_bundle


def test_seed_bundle_meets_documented_minimums() -> None:
    coverage = validate_seed_bundle(load_seed_bundle(), now=datetime(2026, 9, 22, tzinfo=UTC))

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


def test_seed_validation_rejects_missing_activity_coverage() -> None:
    bundle = load_seed_bundle()
    reduced = bundle.model_copy(update={"competitor_activities": bundle.competitor_activities[:2]})

    with pytest.raises(SeedValidationError, match="at least 45"):
        validate_seed_bundle(reduced)


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
