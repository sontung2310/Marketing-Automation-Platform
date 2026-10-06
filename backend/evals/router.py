"""Router suite (evaluation-spec §3.1): classify each golden message, check the decision.

Deterministic checks only: no judge, no MCP, no fixture database. Each message is routed
exactly as `POST /runs` routes it, against a stub session holding 3 recommendations and
one deliverable. A case passes when the routed outcome (a run's agent and intent, a
clarification or an out-of-scope answer), and any expected deliverable type, references
and answer message, match its `expect` block.
"""

import asyncio
import time

from pydantic import BaseModel

from app.intelligence.models import AgentName
from app.orchestration.references import Unresolved
from app.orchestration.router import (
    Classifier,
    RouteDecision,
    RouterAnswer,
    classify,
    route_message,
)
from evals.cases import GoldenCase
from evals.report import (
    THRESHOLDS,
    CaseResult,
    Metric,
    Report,
    percentile,
    share,
)

# A router answer reads as the NONE agent with its own intent, like the golden cases.
ANSWER_INTENT = {"NEEDS_CLARIFICATION": "CLARIFY", "OUT_OF_SCOPE": "OUT_OF_SCOPE"}
SAFE_PREFIXES = ("SAFE-", "RT-OOS")
# The stub session RT-REF cases run against: its latest Strategy run has 3 recommendations.
SESSION_RECOMMENDATIONS = 3


async def session_stub(reference: str) -> dict[str, object] | Unresolved:
    """References resolved as `resolve_reference` would in that session."""
    kind, _, value = reference.partition(":")
    if kind == "recommendation" and value.isdecimal():
        if 1 <= int(value) <= SESSION_RECOMMENDATIONS:
            return {"id": f"rec_stub_{value}", "ordinal": int(value)}
        return Unresolved(f"No recommendation #{value} in this session")
    if reference == "deliverable:last":
        return {"id": "del_stub_last"}
    return Unresolved(f"I could not tell what {reference!r} refers to")


class RouterRecord(BaseModel):
    case_id: str
    repeat: int
    decision: RouteDecision | None
    status: str | None  # RUN, NEEDS_CLARIFICATION or OUT_OF_SCOPE
    agent: str | None
    intent: str | None
    answer: str | None = None  # the router's message when no run starts
    seconds: float
    error: str | None = None


async def route_case(case: GoldenCase, repeat: int, classifier: Classifier) -> RouterRecord:
    hint = case.input.agent_hint
    agent_hint = None if hint == "AUTO" else AgentName(hint)
    started = time.perf_counter()
    try:
        decision, outcome, _ = await route_message(
            classifier, session_stub, case.input.message or "", agent_hint
        )
    except Exception as exc:  # recorded as a failed case, never a crashed suite
        seconds = time.perf_counter() - started
        return RouterRecord(
            case_id=case.id,
            repeat=repeat,
            decision=None,
            status=None,
            agent=None,
            intent=None,
            seconds=seconds,
            error=f"{type(exc).__name__}: {exc}"[:200],
        )
    seconds = time.perf_counter() - started
    status: str
    answer = None
    if isinstance(outcome, RouterAnswer):
        status, agent, intent = outcome.status, "NONE", ANSWER_INTENT[outcome.status]
        answer = outcome.message
    else:
        status, agent, intent = "RUN", str(outcome.agent), str(outcome.intent)
    return RouterRecord(
        case_id=case.id,
        repeat=repeat,
        decision=decision,
        status=status,
        agent=agent,
        intent=intent,
        answer=answer,
        seconds=seconds,
    )


async def run_router(
    cases: list[GoldenCase],
    *,
    repeats: int,
    concurrency: int,
    classifier: Classifier = classify,
) -> list[RouterRecord]:
    gate = asyncio.Semaphore(concurrency)

    async def one(case: GoldenCase, repeat: int) -> RouterRecord:
        async with gate:
            return await route_case(case, repeat, classifier)

    jobs = [one(case, repeat) for case in cases for repeat in range(1, repeats + 1)]
    return list(await asyncio.gather(*jobs))


def router_checks(case: GoldenCase, record: RouterRecord) -> dict[str, bool]:
    expected = case.expect.route
    checks = {"status": record.status in case.expect.status}
    if case.expect.answer is not None:
        checks["answer"] = record.answer == case.expect.answer
    if expected is not None:
        checks["route"] = record.agent == expected.agent and (
            expected.intent is None or record.intent == expected.intent
        )
        if expected.deliverable_type is not None:
            decided = record.decision.deliverable_type if record.decision else None
            checks["deliverable_type"] = decided == expected.deliverable_type
        if expected.references is not None:
            references = record.decision.references if record.decision else []
            checks["references"] = sorted(references) == sorted(expected.references)
    return checks


def build_router_report(
    cases: list[GoldenCase], records: list[RouterRecord], repeats: int
) -> Report:
    by_case: dict[str, list[RouterRecord]] = {case.id: [] for case in cases}
    for record in records:
        by_case.setdefault(record.case_id, []).append(record)
    results: list[CaseResult] = []
    for case in cases:
        runs = sorted(by_case[case.id], key=lambda r: r.repeat)
        checked = [router_checks(case, r) for r in runs]
        passes = [r.error is None and all(c.values()) for r, c in zip(runs, checked, strict=True)]
        first = runs[0] if runs else None
        results.append(
            CaseResult(
                case_id=case.id,
                category=case.category,
                expected_runs=repeats,
                passes=passes,
                failed_checks=sorted({name for c in checked for name, ok in c.items() if not ok}),
                errors=sorted({r.error for r in runs if r.error}),
                excerpt=(
                    f"{first.status} {first.agent} {first.intent}: "
                    f"{first.decision.reason if first.decision else first.error}"
                )[:200]
                if first
                else "no run",
            )
        )
    categories: dict[str, list[bool]] = {}
    for result in results:
        categories.setdefault(result.category, []).append(result.passed_all)
    category_share = {name: share(values) for name, values in sorted(categories.items())}
    safe = [r.passed_all for r in results if r.category.startswith(SAFE_PREFIXES)]
    tagged = zip(results, cases, strict=True)
    demo = [result.passed_all for result, case in tagged if "demo-path" in case.tags]
    seconds = [r.seconds for r in records if r.error is None]
    actuals: dict[str, float | None] = {
        "pass_all_overall": share([r.passed_all for r in results]),
        "pass_all_per_category": min(category_share.values(), default=0.0),
        "safe_categories": share(safe) if safe else 1.0,
        "demo_path": share(demo) if demo else 1.0,
        "p95_latency_s_max": percentile(seconds, 95) if seconds else None,
    }
    metrics = [
        Metric(
            name=name,
            actual=actual,
            threshold=limit,
            passed=actual is not None
            and (actual <= limit if name.endswith("_max") else actual >= limit),
        )
        for name, limit in THRESHOLDS["router"].items()
        if name != "pass_all_per_category" or repeats >= 3
        for actual in [actuals[name]]
    ]
    return Report(
        suite="router",
        runs=len(records),
        judge_complete=True,  # the router suite has no judge (evaluation-spec §6: n/a)
        metrics=metrics,
        categories=category_share,
        cases=results,
        judge_means={},
        lowest_scored=[],
        tokens={},
        latency_s={"p50": percentile(seconds, 50), "p95": percentile(seconds, 95)}
        if seconds
        else {},
    )
