import pytest

from app.pipelines.seed.loader import SeedValidationError, load_seed_bundle, validate_seed_bundle


def test_seed_bundle_meets_documented_minimums() -> None:
    coverage = validate_seed_bundle(load_seed_bundle())

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
