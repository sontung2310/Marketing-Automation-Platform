"""The committed Execution golden set meets the evaluation-spec §3.3 coverage contract."""

from collections import Counter

from evals.cases import check_fixture_ids, golden_path, parse_cases
from evals.fixture import load_fixture

# evaluation-spec §3.3: category -> minimum number of cases.
MINIMUMS = {
    "EX-SIM-BLOG": 4,
    "EX-SIM-SOCIAL": 5,
    "EX-SIM-CEO": 4,
    "EX-REC": 5,
    "EX-FREE": 6,
    "EX-OUTREACH": 3,
    "EX-CONSTR": 5,
    "EX-REVISE": 3,
    "EX-CLAR": 2,
    "EX-UNSUP": 2,
    "SAFE-PLAG": 3,
    "SAFE-DEFAME": 2,
    "SAFE-INJ": 2,
    "SAFE-FACT": 2,
}
# Deliverable types the trigger-driven categories do not already cover (EX-FREE-<TYPE>).
FREE_TYPES = {"BLOG_OUTLINE", "EMAIL", "AD_COPY", "RESPONSE_BRIEF"}
MAX_UPSTREAM_SHARE = 0.30
CASES = parse_cases(golden_path("execution"))


def test_every_category_meets_its_minimum() -> None:
    counts = Counter(case.category for case in CASES)
    short = {cat: (counts[cat], need) for cat, need in MINIMUMS.items() if counts[cat] < need}
    assert not short, f"categories below their minimum (have, need): {short}"
    assert len(CASES) >= sum(MINIMUMS.values()) == 48


def test_free_form_covers_every_remaining_type() -> None:
    free = {
        c.expect.deliverable.type for c in CASES if c.category == "EX-FREE" and c.expect.deliverable
    }
    assert free >= FREE_TYPES


def test_cases_reference_only_fixture_records() -> None:
    check_fixture_ids(CASES, load_fixture("intelligence_v2"))


def test_upstream_cases_stay_under_thirty_percent() -> None:
    upstream = sum(case.source.startswith("upstream:") for case in CASES)
    assert upstream / len(CASES) <= MAX_UPSTREAM_SHARE


def test_the_demo_path_is_tagged() -> None:
    tagged = {case.category for case in CASES if "demo-path" in case.tags}
    assert {"EX-SIM-BLOG", "EX-SIM-CEO", "EX-REC", "SAFE-PLAG"} <= tagged  # 5-A, 5-B, 5-C, 5-E
