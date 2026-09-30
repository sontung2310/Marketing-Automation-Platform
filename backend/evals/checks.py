"""Deterministic checks (evaluation-spec §5.1). A run passes only if every applicable check does.

Each check returns True (pass), False (fail) or None (not applicable to this case). The
Execution-only checks (deliverable shape, originality, competitor naming) arrive in Step 5.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import ValidationError

from app.agents.strategy.config import SKILL_ALLOWLIST as STRATEGY_SKILLS
from app.agents.strategy.output import StrategyOutput
from app.skills.tools import MAX_LOADS_PER_RUN
from evals.cases import GoldenCase
from evals.fixture import FixtureBundle
from evals.runner import RunRecord

# ponytail: single digits are skipped because counts and ordinals ("3 posts", "#2") are
# not claims; a stricter rule would need the model to cite every number's source.
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
MIN_CHECKED_NUMBER = 10


@dataclass(frozen=True)
class Evaluated:
    """One run with everything the checks read, parsed once."""

    case: GoldenCase
    record: RunRecord
    output: StrategyOutput | None
    tools: list[str]
    cited: set[str]
    fixture: FixtureBundle


def evaluate_inputs(case: GoldenCase, record: RunRecord, fixture: FixtureBundle) -> Evaluated:
    run, output = record.run, None
    if run is not None and run.output is not None:
        try:
            output = StrategyOutput.model_validate(run.output)
        except ValidationError:
            output = None
    tools = [str(call["tool"]) for call in run.tool_calls] if run else []
    cited = {e.id for r in output.recommendations for e in r.evidence} if output else set()
    return Evaluated(case, record, output, tools, cited, fixture)


def claim_text(e: Evaluated) -> str:
    assert e.output is not None
    parts = [e.output.answer, *e.output.implications]
    parts += [f"{r.title} {r.rationale}" for r in e.output.recommendations]
    return " ".join(parts)


def numbers(text: str) -> set[float]:
    """Numeric values, so 5200, 5,200 and 5200.0 are the same claim."""
    found = {float(m.replace(",", "")) for m in NUMBER.findall(text)}
    return {n for n in found if n >= MIN_CHECKED_NUMBER}


def no_invented_numbers(e: Evaluated) -> bool:
    assert e.output is not None
    sources = [e.case.input.message or "", *e.output.assumptions]
    for record_id in {*e.record.retrieved_ids, *e.cited}:
        if (record := e.fixture.record(record_id)) is not None:
            sources.append(json.dumps(record))
    sources += [json.dumps(c.model_dump(mode="json")) for c in e.fixture.companies]
    return numbers(claim_text(e)) <= numbers(" ".join(sources))


def rec_bounds(e: Evaluated) -> bool:
    bounds, output = e.case.expect.recommendations, e.output
    assert bounds is not None and output is not None
    recs = output.recommendations
    ordinals = [r.ordinal for r in recs] == list(range(1, len(recs) + 1))
    kinds = set(bounds.kinds_required) <= {r.kind for r in recs}
    low = bounds.min is None or len(recs) >= bounds.min
    high = bounds.max is None or len(recs) <= bounds.max
    return ordinals and kinds and low and high


def phrases(e: Evaluated) -> bool:
    text = claim_text(e).lower()
    include = e.case.expect.must_include_any
    ok_include = not include or any(p.lower() in text for p in include)
    return ok_include and not any(p.lower() in text for p in e.case.expect.must_not_include)


def skills(e: Evaluated) -> bool:
    assert e.output is not None
    used = {s for r in e.output.recommendations for s in r.skills_used}
    wanted = e.case.expect.skills_any
    return used <= STRATEGY_SKILLS and (not wanted or bool(used & set(wanted)))


def status_in(e: Evaluated) -> bool:
    assert e.output is not None
    return e.output.status in e.case.expect.status


def route_correct(e: Evaluated) -> bool | None:
    route, run = e.case.expect.route, e.record.run
    if route is None or e.case.input.trigger is None or run is None:
        return None  # chat routing is the Step 6 classifier's job
    return (run.agent, run.intent) == (route.agent, route.intent)


def budget(e: Evaluated) -> bool:
    skill_loads = len(e.record.run.skills_loaded) if e.record.run else 0
    return len(e.tools) <= e.case.expect.max_tool_calls and skill_loads <= MAX_LOADS_PER_RUN


Check = Callable[[Evaluated], bool | None]


def needs_output(check: Callable[[Evaluated], bool]) -> Check:
    """Checks on the output content fail (not skip) when there is no valid output."""
    return lambda e: False if e.output is None else check(e)


def when(condition: Callable[[Evaluated], object], check: Check) -> Check:
    return lambda e: check(e) if condition(e) else None


CHECKS: dict[str, Check] = {
    "schema_valid": lambda e: e.output is not None,
    "route_correct": route_correct,
    "status_in": needs_output(status_in),
    "tools_required": when(
        lambda e: e.case.expect.tools_required,
        lambda e: set(e.case.expect.tools_required) <= set(e.tools),
    ),
    "tools_forbidden": when(
        lambda e: e.case.expect.tools_forbidden,
        lambda e: not set(e.case.expect.tools_forbidden) & set(e.tools),
    ),
    "company_context_first": needs_output(
        lambda e: e.tools.count("get_company_context") == 1 and e.tools[0] == "get_company_context"
    ),
    "evidence_grounded": needs_output(
        lambda e: e.cited <= set(e.record.retrieved_ids) and e.cited <= e.fixture.ids()
    ),
    "evidence_required_all": when(
        lambda e: e.case.expect.evidence_required_all,
        needs_output(lambda e: set(e.case.expect.evidence_required_all) <= e.cited),
    ),
    "evidence_required_any": when(
        lambda e: e.case.expect.evidence_required_any,
        needs_output(lambda e: bool(set(e.case.expect.evidence_required_any) & e.cited)),
    ),
    "evidence_forbidden": when(
        lambda e: e.case.expect.evidence_forbidden,
        needs_output(lambda e: not set(e.case.expect.evidence_forbidden) & e.cited),
    ),
    "skills": needs_output(skills),
    "rec_bounds": when(lambda e: e.case.expect.recommendations, needs_output(rec_bounds)),
    "no_invented_numbers": needs_output(no_invented_numbers),
    "phrases": when(
        lambda e: e.case.expect.must_include_any or e.case.expect.must_not_include,
        needs_output(phrases),
    ),
    "budget": budget,
}


def run_checks(case: GoldenCase, record: RunRecord, fixture: FixtureBundle) -> dict[str, bool]:
    """Applicable check results; a run that never started fails schema_valid."""
    evaluated = evaluate_inputs(case, record, fixture)
    results = {name: check(evaluated) for name, check in CHECKS.items()}
    return {name: result for name, result in results.items() if result is not None}
