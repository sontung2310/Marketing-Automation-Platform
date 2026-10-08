"""The committed Strategy golden set meets the evaluation-spec §3.2 coverage contract."""

from collections import Counter

from evals.cases import check_fixture_ids, golden_path, parse_cases
from evals.fixture import load_fixture

# evaluation-spec §3.2: category -> minimum number of cases.
MINIMUMS = {
    "ST-TOPIC": 6,
    "ST-SYNTH": 4,  # Step 7b: Generate strategy and focused synthesis
    **{
        f"ST-RESP-{t}": 2
        for t in (
            "NEW_PRODUCT",
            "PRODUCT_REMOVED",
            "PRICE_CHANGE",
            "PROMOTION",
            "CAMPAIGN_LAUNCH",
            "PAGE_UPDATE",
        )
    },
    **{f"ST-WHY-{t}": 2 for t in ("NEW_BLOG", "SOCIAL_POST", "EXECUTIVE_POST")},
    "ST-INFL": 4,
    "ST-TREND": 3,
    "ST-COMP": 3,
    "ST-GAP": 4,
    "ST-STALE": 2,
    "ST-CLAR": 2,
    "ST-MULTI": 2,
    "ST-MISROUTE": 1,
    "SAFE-INJ": 2,
    "SAFE-UNETH": 1,
}
MAX_UPSTREAM_SHARE = 0.30
CASES = parse_cases(golden_path("strategy"))


def test_every_category_meets_its_minimum() -> None:
    counts = Counter(case.category for case in CASES)
    short = {cat: (counts[cat], need) for cat, need in MINIMUMS.items() if counts[cat] < need}
    assert not short, f"categories below their minimum (have, need): {short}"
    assert len(CASES) >= sum(MINIMUMS.values()) == 52


def test_cases_reference_only_fixture_records() -> None:
    check_fixture_ids(CASES, load_fixture("intelligence_v2"))


def test_upstream_cases_stay_under_thirty_percent() -> None:
    upstream = sum(case.source.startswith("upstream:") for case in CASES)
    assert upstream / len(CASES) <= MAX_UPSTREAM_SHARE


def test_the_demo_path_is_tagged() -> None:
    assert any("demo-path" in case.tags for case in CASES)


def test_every_case_that_recommends_stays_within_five() -> None:
    for case in CASES:
        bounds = case.expect.recommendations
        assert bounds is None or bounds.max is None or bounds.max <= 5, case.id


def test_why_it_matters_never_recommends() -> None:
    for case in CASES:
        trigger = case.input.trigger
        if trigger is not None and trigger.action == "WHY_IT_MATTERS":
            assert case.expect.recommendations is not None, case.id
            assert case.expect.recommendations.max == 0, case.id
