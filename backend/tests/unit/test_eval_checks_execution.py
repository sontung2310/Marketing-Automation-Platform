"""Execution eval checks: deliverable shape, originality, competitor naming and actions."""

from collections.abc import Callable
from typing import Any

import pytest

from evals.cases import GoldenCase
from evals.checks import CHECKS, run_checks
from evals.fixture import load_fixture
from evals.runner import RunRecord
from tests.execution_samples import deliverable, execution_output
from tests.strategy_samples import golden_case, sample_run
from tests.unit.test_eval_checks import EXECUTION_CHECKS
from tests.unit.test_eval_checks import FAILURES as STRATEGY_FAILURES

FIXTURE = load_fixture("intelligence_v2")
TRIGGER = "act_seed_006"  # Brightlane LinkedIn post: "Start with the customer question, ..."
BLOG = "act_seed_001"  # retrieved in the run; its excerpt is long enough to copy from
COPIED = (
    "Before you plan a single post, list the ten questions your best customers asked during "
    "their last buying cycle."
)
ORIGINAL = (
    "We help B2B teams plan around what buyers actually ask. Strong content starts with "
    "listening first and writing second."
)


def base_case(**expect: Any) -> GoldenCase:
    return golden_case(
        id="EX-T",
        suite="execution",
        category="EX-SIM-SOCIAL",
        input={"trigger": {"kind": "FEED_ACTION", "ref_id": TRIGGER, "action": "CREATE_SIMILAR"}},
        expect={
            "status": ["OK"],
            "evidence_required_all": [TRIGGER],
            "skills_any": ["social"],
            "deliverable": {"type": "LINKEDIN_POST", "channel": "LINKEDIN", "max_chars": 3000},
            "proposed_actions_any": ["schedule_social_post"],
        }
        | expect,
    )


def base_run() -> dict[str, Any]:
    output = execution_output(deliverable(body=ORIGINAL), evidence_ids=(TRIGGER,))
    return {
        "agent": "EXECUTION",
        "intent": "CREATE_SIMILAR",
        "status": "SUCCEEDED",
        "trigger": {"kind": "FEED_ACTION", "ref_id": TRIGGER, "action": "CREATE_SIMILAR"},
        "output": output.model_dump(mode="json"),
        "tool_calls": [{"tool": "get_company_context"}, {"tool": "get_competitor_activity"}],
        "skills_loaded": ["social"],
    }


def record(run: dict[str, Any]) -> RunRecord:
    return RunRecord(
        case_id="EX-T",
        repeat=1,
        run=sample_run(**run),
        retrieved_ids=["cmp_marketing_eye", TRIGGER, BLOG],
    )


def with_body(body: str) -> Callable[[dict[str, Any]], None]:
    return lambda o: o["deliverable"].update(body_markdown=body)


def changed(change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    run = base_run()
    change(run["output"])
    return run


def test_a_good_execution_run_passes_every_applicable_check() -> None:
    results = run_checks(base_case(), record(base_run()), FIXTURE)
    assert set(results) >= EXECUTION_CHECKS
    assert all(results.values()), {k: v for k, v in results.items() if not v}


EXECUTION_FAILURES: list[tuple[str, dict[str, Any]]] = [
    ("deliverable_shape", changed(lambda o: o["deliverable"].update(type="X_POST"))),
    ("originality", changed(with_body(f"{ORIGINAL} {COPIED}"))),
    ("competitor_naming", changed(with_body(f"Unlike Brightlane, {ORIGINAL}"))),
    ("proposed_actions_any", changed(lambda o: o.update(proposed_actions=[]))),
]


@pytest.mark.parametrize(
    ("check", "run"), EXECUTION_FAILURES, ids=[f[0] for f in EXECUTION_FAILURES]
)
def test_each_execution_check_catches_its_failure(check: str, run: dict[str, Any]) -> None:
    assert run_checks(base_case(), record(run), FIXTURE)[check] is False


def test_deliverable_limits_first_person_and_persona() -> None:
    long_case = base_case(deliverable={"max_words": 5})
    assert run_checks(long_case, record(base_run()), FIXTURE)["deliverable_shape"] is False
    ceo_case = base_case(
        deliverable={"first_person": True, "author_persona_includes": "Morgan Hale"}
    )
    assert run_checks(ceo_case, record(base_run()), FIXTURE)["deliverable_shape"] is False
    ceo = changed(
        lambda o: o["deliverable"].update(
            body_markdown="My view: plan around buyers.", author_persona="Morgan Hale, CEO"
        )
    )
    assert run_checks(ceo_case, record(ceo), FIXTURE)["deliverable_shape"] is True


def test_naming_a_competitor_the_user_asked_about_is_fine() -> None:
    case = base_case()
    case = case.model_copy(
        update={"input": case.input.model_copy(update={"message": "Mention Brightlane"})}
    )
    run = changed(with_body(f"Unlike Brightlane, {ORIGINAL}"))
    assert run_checks(case, record(run), FIXTURE)["competitor_naming"] is True


def test_every_check_has_a_failure_case() -> None:
    covered = {f[0] for f in STRATEGY_FAILURES} | {f[0] for f in EXECUTION_FAILURES}
    assert covered == set(CHECKS)
