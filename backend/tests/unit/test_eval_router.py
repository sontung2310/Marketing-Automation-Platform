"""Router eval suite: run, check and report with a stub classifier (no model)."""

import asyncio

from app.intelligence.models import AgentName
from app.orchestration.router import RouteDecision
from evals.cases import GoldenCase
from evals.router import build_router_report, router_checks, run_router


def case(case_id: str, category: str, message: str, expect: dict[str, object]) -> GoldenCase:
    return GoldenCase.model_validate(
        {
            "id": case_id,
            "suite": "router",
            "category": category,
            "fixture": "none",
            "description": message,
            "input": {"message": message},
            "expect": expect,
            "tags": ["demo-path"] if category == "RT-EXE" else [],
        }
    )


CASES = [
    case(
        "RT-EXE-01",
        "RT-EXE",
        "Write a LinkedIn post",
        {
            "status": ["RUN"],
            "route": {
                "agent": "EXECUTION",
                "intent": "FREEFORM_DELIVERABLE",
                "deliverable_type": "LINKEDIN_POST",
                "references": [],
            },
        },
    ),
    case(
        "RT-OOS-01",
        "RT-OOS",
        "Weather?",
        {"status": ["OUT_OF_SCOPE"], "route": {"agent": "NONE", "intent": "OUT_OF_SCOPE"}},
    ),
    case(
        "RT-AMB-01",
        "RT-AMB",
        "LinkedIn",
        {"status": ["NEEDS_CLARIFICATION"], "route": {"agent": "NONE", "intent": "CLARIFY"}},
    ),
]

DECISIONS = {
    "Write a LinkedIn post": ("EXECUTION", "FREEFORM_DELIVERABLE", "LINKEDIN_POST", 0.95),
    "Weather?": ("NONE", "OUT_OF_SCOPE", None, 0.99),
    "LinkedIn": ("STRATEGY", "TOPIC_RECOMMENDATION", None, 0.9),  # wrong: should clarify
}


async def stub(message: str, hint: AgentName | None) -> RouteDecision:
    if message == "boom":
        raise RuntimeError("model down")
    agent, intent, deliverable, confidence = DECISIONS[message]
    return RouteDecision.model_validate(
        {
            "agent": agent,
            "intent": intent,
            "deliverable_type": deliverable,
            "references": [],
            "confidence": confidence,
            "reason": "stub",
            "clarification_question": None,
            "clarification_options": [],
        }
    )


def test_router_suite_checks_and_reports() -> None:
    records = asyncio.run(run_router(CASES, repeats=1, concurrency=2, classifier=stub))
    by_id = {r.case_id: r for r in records}
    assert router_checks(CASES[0], by_id["RT-EXE-01"]) == {
        "status": True,
        "route": True,
        "deliverable_type": True,
        "references": True,
    }
    assert router_checks(CASES[2], by_id["RT-AMB-01"]) == {"status": False, "route": False}

    report = build_router_report(CASES, records, repeats=1)
    metrics = {m.name: m for m in report.metrics}
    assert metrics["pass_all_overall"].actual == 2 / 3
    assert not metrics["pass_all_overall"].passed
    assert metrics["safe_categories"].passed and metrics["demo_path"].passed
    assert "pass_all_per_category" not in metrics  # one repeat
    assert report.categories == {"RT-AMB": 0.0, "RT-EXE": 1.0, "RT-OOS": 1.0}


def test_a_failing_classifier_fails_its_case_not_the_suite() -> None:
    broken = case("RT-STR-01", "RT-STR", "boom", {"status": ["RUN"]})
    [record] = asyncio.run(run_router([broken], repeats=1, concurrency=1, classifier=stub))
    assert record.error == "RuntimeError: model down"
    report = build_router_report([broken], [record], repeats=1)
    assert report.cases[0].errors == ["RuntimeError: model down"]
