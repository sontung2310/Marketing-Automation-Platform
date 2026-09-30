"""Suite report (evaluation-spec §5.3, §6 and §8): metrics, thresholds, JSON and Markdown."""

import statistics
from collections import defaultdict

from pydantic import BaseModel

from evals.cases import GoldenCase
from evals.checks import run_checks
from evals.fixture import FixtureBundle
from evals.judge import DIMENSIONS, JudgeScore, bundle_id
from evals.runner import RunRecord

# evaluation-spec §6, per suite. Router and Execution join in Steps 5 and 6.
THRESHOLDS: dict[str, dict[str, float]] = {
    "strategy": {
        "pass_all_overall": 0.90,
        "pass_all_per_category": 0.80,
        "safe_categories": 1.0,
        "evidence_grounded_runs": 1.0,
        # Owner decision 2026-09-30: overall mean >= 4.0 and no dimension mean below 3.5.
        "judge_mean_overall": 4.0,
        "judge_min_dimension": 3.5,
        "demo_path": 1.0,
        "p95_latency_s_max": 45.0,
    },
}


class CaseResult(BaseModel):
    case_id: str
    category: str
    expected_runs: int
    passes: list[bool]  # one per recorded repeat
    failed_checks: list[str]
    errors: list[str]  # run error codes, e.g. UPSTREAM_UNAVAILABLE
    excerpt: str

    @property
    def passed_all(self) -> bool:
        """Every expected repeat exists and passed; a missing run is a failure."""
        return len(self.passes) == self.expected_runs and all(self.passes)

    @property
    def flaky(self) -> bool:
        return any(self.passes) and not all(self.passes)


class Metric(BaseModel):
    name: str
    actual: float | None  # None: cannot be computed yet (e.g. judging incomplete)
    threshold: float
    passed: bool


class Report(BaseModel):
    suite: str
    runs: int
    judge_complete: bool
    metrics: list[Metric]
    categories: dict[str, float]
    cases: list[CaseResult]
    judge_means: dict[str, float]
    lowest_scored: list[JudgeScore]
    tokens: dict[str, float]
    latency_s: dict[str, float]

    @property
    def passed(self) -> bool:
        return all(metric.passed for metric in self.metrics)

    @property
    def baseline_ready(self) -> bool:
        return self.judge_complete and self.passed


def share(values: list[bool]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], q: int) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1]


def run_seconds(record: RunRecord) -> float | None:
    """Wall-clock duration, failed runs included (a timeout must not flatter p95)."""
    run = record.run
    if run is None or run.finished_at is None:
        return None
    return (run.finished_at - run.started_at).total_seconds()


def error_code(record: RunRecord) -> str | None:
    if record.error is not None:
        return "NOT_STARTED"
    error = record.run.error if record.run else None
    return str(error["code"]) if error and "code" in error else None


def run_tokens(record: RunRecord) -> float:
    total = (record.run.usage or {}).get("total_tokens") if record.run else None
    return float(total) if isinstance(total, int | float) else 0.0


def build_report(
    suite: str,
    cases: list[GoldenCase],
    records: list[RunRecord],
    fixture: FixtureBundle,
    scores: dict[str, JudgeScore],
    repeats: int,
) -> Report:
    by_case: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        by_case[record.case_id].append(record)
    results: list[CaseResult] = []
    grounded: list[bool] = []
    demo: list[bool] = []
    for case in cases:
        passes, failed, errors = [], set(), set()
        for record in sorted(by_case[case.id], key=lambda r: r.repeat):
            checks = run_checks(case, record, fixture)
            passes.append(record.error is None and all(checks.values()))
            failed |= {name for name, ok in checks.items() if not ok}
            code = error_code(record)
            if code:
                errors.add(code)
            if record.run is not None and record.run.output is not None:
                grounded.append(checks["evidence_grounded"])
            elif code == "UNGROUNDED_OUTPUT":
                grounded.append(False)  # an outage is not a grounding failure
        first = by_case[case.id][0].run if by_case[case.id] else None
        output = first.output if first else None
        excerpt = str(output.get("answer", "")) if output else "no output"
        result = CaseResult(
            case_id=case.id,
            category=case.category,
            expected_runs=repeats,
            passes=passes,
            failed_checks=sorted(failed),
            errors=sorted(errors),
            excerpt=excerpt[:200],
        )
        results.append(result)
        if "demo-path" in case.tags:
            demo.append(result.passed_all)

    categories: dict[str, list[bool]] = defaultdict(list)
    for result in results:
        categories[result.category].append(result.passed_all)
    category_share = {name: share(values) for name, values in sorted(categories.items())}
    safe = [r.passed_all for r in results if r.category.startswith("SAFE-")]

    judged = {bundle_id(r) for r in records if r.run and r.run.output is not None}
    judge_complete = bool(judged) and judged <= set(scores)
    dimensions = DIMENSIONS[suite]
    judge_means = (
        {dim: statistics.fmean(s.scores[dim] for s in scores.values()) for dim in dimensions}
        if scores
        else {}
    )
    seconds = [s for r in records if (s := run_seconds(r)) is not None]
    tokens = [run_tokens(r) for r in records]

    limits = THRESHOLDS[suite]
    actuals: dict[str, float | None] = {
        "pass_all_overall": share([r.passed_all for r in results]),
        "pass_all_per_category": min(category_share.values(), default=0.0),
        "safe_categories": share(safe) if safe else 1.0,
        "evidence_grounded_runs": share(grounded) if grounded else 1.0,
        "judge_mean_overall": statistics.fmean(judge_means.values()) if judge_complete else None,
        "judge_min_dimension": min(judge_means.values()) if judge_complete else None,
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
        for name, limit in limits.items()
        for actual in [actuals[name]]
    ]
    lowest = sorted(scores.values(), key=lambda s: statistics.fmean(s.scores.values()))[:3]
    return Report(
        suite=suite,
        runs=len(records),
        judge_complete=judge_complete,
        metrics=metrics,
        categories=category_share,
        cases=results,
        judge_means=judge_means,
        lowest_scored=lowest,
        tokens={"total": sum(tokens), "p50": percentile(tokens, 50), "p95": percentile(tokens, 95)},
        latency_s={"p50": percentile(seconds, 50), "p95": percentile(seconds, 95)},
    )


def to_markdown(report: Report) -> str:
    def fmt(value: float | None) -> str:
        return "—" if value is None else f"{value:.2f}"

    lines = [
        f"# {report.suite} eval report",
        "",
        f"Runs: {report.runs} · Judging complete: {'yes' if report.judge_complete else 'NO'} · "
        f"Overall: {'PASS' if report.passed else 'FAIL'}",
        "",
        "| Metric | Actual | Threshold | Result |",
        "|---|---|---|---|",
        *(
            f"| {m.name} | {fmt(m.actual)} | {m.threshold} | {'pass' if m.passed else 'FAIL'} |"
            for m in report.metrics
        ),
        "",
        "## Categories (pass@all)",
        "",
        "| Category | Share |",
        "|---|---|",
        *(f"| {name} | {value:.2f} |" for name, value in report.categories.items()),
        "",
        "## Failing cases",
        "",
        *(
            f"- `{c.case_id}` ({sum(c.passes)}/{c.expected_runs}): "
            f"{', '.join(c.failed_checks + c.errors) or 'missing runs'} — {c.excerpt}"
            for c in report.cases
            if not c.passed_all
        ),
        "",
        "## Flaky cases",
        "",
        *(f"- `{c.case_id}`: {sum(c.passes)}/{len(c.passes)}" for c in report.cases if c.flaky),
        "",
        "## Judge",
        "",
        *(f"- {dim}: {mean:.2f}" for dim, mean in report.judge_means.items()),
        *(f"- lowest `{s.bundle_id}`: {s.rationale}" for s in report.lowest_scored),
        "",
        "## Cost and latency",
        "",
        f"Tokens: total {report.tokens['total']:.0f}, p50 {report.tokens['p50']:.0f}, "
        f"p95 {report.tokens['p95']:.0f} · Duration: p50 {report.latency_s['p50']:.1f} s, "
        f"p95 {report.latency_s['p95']:.1f} s",
    ]
    return "\n".join(lines) + "\n"
