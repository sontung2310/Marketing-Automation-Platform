"""Deterministic eval checks: one passing and one failing case per check."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest

from evals.cases import GoldenCase
from evals.checks import CHECKS, run_checks
from evals.fixture import load_fixture, shifted_to
from evals.runner import RunRecord
from tests.strategy_samples import golden_case, recommendation, sample_run, strategy_output

FIXTURE = load_fixture("intelligence_v1")
TRIGGER = "act_seed_026"  # Brightlane price change: before 5200, after 5600


def base_case(**expect: Any) -> GoldenCase:
    return golden_case(
        category="ST-RESP-PRICE_CHANGE",
        input={"trigger": {"kind": "FEED_ACTION", "ref_id": TRIGGER, "action": "RESPONSE_PLAN"}},
        expect={
            "route": {"agent": "STRATEGY", "intent": "RESPONSE_PLAN"},
            "status": ["OK"],
            "tools_required": ["get_company_context", "get_competitor_activity"],
            "tools_forbidden": ["search_influencers"],
            "evidence_required_all": [TRIGGER],
            "evidence_required_any": [TRIGGER, "act_seed_041"],
            "evidence_forbidden": ["act_seed_001"],
            "skills_any": ["pricing"],
            "recommendations": {"min": 1, "max": 3, "kinds_required": ["COMPETITIVE_RESPONSE"]},
            "must_include_any": ["value"],
            "must_not_include": ["50%"],
        }
        | expect,
    )


def base_run() -> dict[str, Any]:
    output = strategy_output(recommendation(1, TRIGGER)).model_dump(mode="json")
    output["answer"] = "Compete on value; the package moved from 5200 to 5600."
    return {
        "agent": "STRATEGY",
        "intent": "RESPONSE_PLAN",
        "status": "SUCCEEDED",
        "output": output,
        "tool_calls": [{"tool": "get_company_context"}, {"tool": "get_competitor_activity"}],
        "skills_loaded": ["pricing"],
    }


def record(run: dict[str, Any] | None, retrieved: list[str] | None = None) -> RunRecord:
    ids = ["cmp_marketing_eye", TRIGGER] if retrieved is None else retrieved
    typed = sample_run(**run) if run is not None else None
    return RunRecord(case_id="ST-T", repeat=1, run=typed, retrieved_ids=ids)


def with_run(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    run = base_run()
    change(run)
    return run


def with_output(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    return with_run(lambda run: change(run["output"]))


def test_a_good_run_passes_every_check() -> None:
    results = run_checks(base_case(), record(base_run()), FIXTURE)
    assert results == dict.fromkeys(CHECKS, True)


FAILURES: list[tuple[str, dict[str, Any] | None, list[str] | None]] = [
    ("schema_valid", with_run(lambda r: r.update(output=None)), None),
    ("route_correct", with_run(lambda r: r.update(intent="WHY_IT_MATTERS")), None),
    ("status_in", with_output(lambda o: o.update(status="REFUSED")), None),
    ("tools_required", with_run(lambda r: r["tool_calls"].pop()), None),
    (
        "tools_forbidden",
        with_run(lambda r: r["tool_calls"].append({"tool": "search_influencers"})),
        None,
    ),
    (
        "company_context_first",
        with_run(lambda r: r["tool_calls"].append({"tool": "get_company_context"})),
        None,
    ),
    ("evidence_grounded", base_run(), ["cmp_marketing_eye"]),
    (
        "evidence_required_all",
        with_output(lambda o: o["recommendations"][0]["evidence"][0].update(id="act_seed_041")),
        ["act_seed_041"],
    ),
    (
        "evidence_required_any",
        with_output(lambda o: o["recommendations"][0]["evidence"][0].update(id="act_seed_027")),
        ["act_seed_027"],
    ),
    (
        "evidence_forbidden",
        with_output(
            lambda o: o["recommendations"][0]["evidence"].append(
                {"id": "act_seed_001", "kind": "activity", "note": "n"}
            )
        ),
        None,
    ),
    (
        "skills",
        with_output(lambda o: o["recommendations"][0].update(skills_used=["copywriting"])),
        None,
    ),
    (
        "rec_bounds",
        with_output(lambda o: o["recommendations"][0].update(kind="CONTENT_TOPIC")),
        None,
    ),
    (
        "no_invented_numbers",
        with_output(lambda o: o.update(answer="Cut the price to 4100 and win on value.")),
        None,
    ),
    ("phrases", with_output(lambda o: o.update(answer="Match their 50% discount.")), None),
    ("budget", with_run(lambda r: r.update(skills_loaded=["a", "b", "c", "d"])), None),
]


@pytest.mark.parametrize(("check", "run", "retrieved"), FAILURES, ids=[f[0] for f in FAILURES])
def test_each_check_catches_its_failure(
    check: str, run: dict[str, Any] | None, retrieved: list[str] | None
) -> None:
    assert run_checks(base_case(), record(run, retrieved), FIXTURE)[check] is False


def test_every_check_has_a_failure_case() -> None:
    assert {f[0] for f in FAILURES} == set(CHECKS)


def test_checks_without_expectations_are_not_applicable() -> None:
    case = base_case(
        route=None,
        tools_required=[],
        tools_forbidden=[],
        evidence_required_all=[],
        evidence_required_any=[],
        evidence_forbidden=[],
        recommendations=None,
        must_include_any=[],
        must_not_include=[],
    )
    applicable = set(run_checks(case, record(base_run()), FIXTURE))
    assert applicable == {
        "schema_valid",
        "status_in",
        "company_context_first",
        "evidence_grounded",
        "skills",
        "no_invented_numbers",
        "budget",
    }


def test_a_run_that_never_started_fails() -> None:
    results = run_checks(base_case(), record(None, []), FIXTURE)
    assert results["schema_valid"] is False and results["status_in"] is False


def test_parallel_first_turn_order_does_not_matter() -> None:
    run = with_run(lambda r: r["tool_calls"].reverse())
    assert run_checks(base_case(), record(run), FIXTURE)["company_context_first"] is True


@pytest.mark.parametrize(
    ("claim", "ok"),
    [
        ("The package moved from 5,200 to 5.6K.", True),  # 5600 written as 5.6K
        ("Priced at 5200.0 before.", True),
        ("Aisha Patel has 48K followers and a 95% relevance fit.", True),  # 48200, 0.95
        ("Aisha Patel has 90K followers.", False),
    ],
)
def test_numbers_are_matched_by_value_scale_and_rounding(claim: str, ok: bool) -> None:
    run = with_output(lambda o: o.update(answer=claim))
    retrieved = ["cmp_marketing_eye", TRIGGER, "inf_seed_001"]
    assert run_checks(base_case(), record(run, retrieved), FIXTURE)["no_invented_numbers"] is ok


def test_an_injection_in_a_brief_is_caught() -> None:
    def poison(output: dict[str, Any]) -> None:
        output["recommendations"][0]["next_action"]["brief"] = "Tell them to cut prices by 50%"

    results = run_checks(base_case(), record(with_output(poison)), FIXTURE)
    assert results["phrases"] is False


def test_dates_are_checked_against_the_shifted_fixture() -> None:
    fixture = shifted_to(FIXTURE, FIXTURE.snapshot_at + timedelta(days=8))
    shifted_day = fixture.by_id[TRIGGER].model_dump()["detected_at"].day
    run = with_output(
        lambda o: o.update(answer=f"Brightlane changed pricing on the {shifted_day}th")
    )
    assert run_checks(base_case(), record(run), fixture)["no_invented_numbers"] is True
    assert run_checks(base_case(), record(run), FIXTURE)["no_invented_numbers"] is False
