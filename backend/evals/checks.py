"""Deterministic checks (evaluation-spec §5.1). A run passes only if every applicable check does.

Each check returns True (pass), False (fail) or None (not applicable to this case). What a
suite's output means (cited IDs, claims, skills) comes from its SuiteSpec.
"""

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ValidationError

from app.agents.common.mcp import collect_activity_competitors
from app.agents.execution.guards import (
    FIRST_PERSON,
    MAX_JACCARD,
    MAX_SHARED_RUN,
    activity_texts,
    jaccard,
    longest_shared_run,
    named_competitors,
)
from app.agents.execution.output import ExecutionOutput
from app.agents.strategy.output import StrategyOutput
from app.agents.strategy.validation import niche_problems
from app.orchestration.routing import TriggerAction
from app.skills.tools import MAX_LOADS_PER_RUN
from evals.cases import GoldenCase
from evals.fixture import FixtureBundle
from evals.runner import RunRecord
from evals.suites import SUITES, SuiteSpec

# ponytail: single digits are skipped because counts and ordinals ("3 posts", "#2") are
# not claims; a stricter rule would need the model to cite every number's source.
# A K/M suffix counts only as a whole unit: "275 mentions" is 275, not 275 million.
NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM](?![A-Za-z])|%)?")
MIN_CHECKED_NUMBER = 10
# A proposed meeting length ("a 20-minute call") is an offer, not a factual claim.
OFFERED_DURATION = re.compile(r"\b\d+-(?:minute|hour)\b")
# A suggested count ("10-15 questions", "3-5 takeaways") is advice on structure, not a
# claim about the world (design D12 gap 6: guidance quantities are not invented figures).
ADVISORY_COUNT = re.compile(
    r"\b\d+(?:\s*(?:-|\u2013)\s*\d+)?\s+"
    r"(?:questions?|tips?|steps?|ideas?|takeaways?|examples?|sections?|bullets?"
    r"|topics?|options?|ways?)\b",
    re.IGNORECASE,
)
# Numbers the agents' own policies use ("older than 21 days", X's "280-character limit",
# the 800-1,500 word blog range); not claims about data.
POLICY_NUMBERS = "21 280 2200 3000 800 1500"
DATE_FIELDS = ("detected_at", "occurred_at", "computed_at")


def record_ages(record: dict[str, object], now: datetime) -> list[str]:
    """A record's real age in days ("74 days old" is a fact, not an invented number)."""
    days = [
        (now - datetime.fromisoformat(str(record[f]).replace("Z", "+00:00"))).days
        for f in DATE_FIELDS
        if record.get(f)
    ]
    return [str(d + offset) for d in days for offset in (0, 1)]  # whole days, either rounding


SCALE = {"k": 1e3, "m": 1e6}
# "48K followers" for 48,200 is a rounding, not an invention.
ROUNDING_TOLERANCE = 0.01


@dataclass(frozen=True)
class Evaluated:
    """One run with everything the checks read, parsed once."""

    case: GoldenCase
    record: RunRecord
    output: BaseModel | None
    tools: list[str]
    cited: set[str]
    fixture: FixtureBundle
    spec: SuiteSpec


def evaluate_inputs(case: GoldenCase, record: RunRecord, fixture: FixtureBundle) -> Evaluated:
    spec = SUITES[case.suite]
    run, output = record.run, None
    if run is not None and run.output is not None:
        try:
            output = spec.output_type.model_validate(run.output)
        except ValidationError:
            output = None
    tools = [str(c["tool"]) for c in run.tool_calls] if run else []
    cited = spec.cited(output) if output else set()
    return Evaluated(case, record, output, tools, cited, fixture, spec)


def strategy(e: Evaluated) -> StrategyOutput:
    assert isinstance(e.output, StrategyOutput)
    return e.output


def execution(e: Evaluated) -> ExecutionOutput:
    assert isinstance(e.output, ExecutionOutput)
    return e.output


def claim_text(e: Evaluated) -> str:
    assert e.output is not None
    return e.spec.claims(e.output)


def claimed_values(text: str) -> list[set[float]]:
    """Each checked number as the values it may stand for: 48.2K -> 48200, 95% -> 95 or 0.95."""
    claims = []
    stripped = ADVISORY_COUNT.sub("", OFFERED_DURATION.sub("", text))
    for digits, suffix in NUMBER.findall(stripped):
        value = float(digits.replace(",", ""))
        if value < MIN_CHECKED_NUMBER:
            continue
        value *= SCALE.get(suffix.lower(), 1)
        claims.append({value, value / 100} if suffix == "%" else {value})
    return claims


def source_values(text: str) -> list[float]:
    return [float(digits.replace(",", "")) for digits, _ in NUMBER.findall(text)]


def no_invented_numbers(e: Evaluated) -> bool:
    assert e.output is not None
    assumptions: list[str] = getattr(e.output, "assumptions", [])
    # The prompt hands the agent today's date (ISO, common/prompt.py); citing it
    # for staleness ("as of 2026-10-12") is not an invented number (design D9).
    today = e.fixture.snapshot_at.date().isoformat()
    sources = [e.case.input.message or "", *assumptions, POLICY_NUMBERS, today]
    for record_id in {*e.record.retrieved_ids, *e.cited}:
        if (record := e.fixture.record(record_id)) is not None:
            sources += [json.dumps(record), *record_ages(record, e.fixture.snapshot_at)]
    sources += [json.dumps(c.model_dump(mode="json")) for c in e.fixture.companies]
    sources += [json.dumps(r, default=str) for r in e.record.tool_results]  # e.g. summary counts
    if e.record.run:  # the agent's own search window ("in the last 365 days")
        sources += [str(call.get("args_summary", "")) for call in e.record.run.tool_calls]
    known = source_values(" ".join(sources))
    return all(
        any(math.isclose(c, k, rel_tol=ROUNDING_TOLERANCE) for c in claim for k in known)
        for claim in claimed_values(claim_text(e))
    )


def rec_bounds(e: Evaluated) -> bool:
    bounds, output = e.case.expect.recommendations, strategy(e)
    assert bounds is not None
    recs = output.recommendations
    kinds = set(bounds.kinds_required) <= {r.kind for r in recs}
    low = bounds.min is None or len(recs) >= bounds.min
    high = bounds.max is None or len(recs) <= bounds.max
    return kinds and low and high


def phrases(e: Evaluated) -> bool:
    assert e.output is not None
    text, published = claim_text(e).lower(), e.spec.published(e.output).lower()
    include = e.case.expect.must_include_any
    ok_include = not include or any(p.lower() in text for p in include)
    return ok_include and not any(p.lower() in published for p in e.case.expect.must_not_include)


def data_gaps(e: Evaluated) -> bool:
    gaps = " ".join(strategy(e).data_gaps).lower()
    return any(phrase.lower() in gaps for phrase in e.case.expect.data_gaps_any)


def channels(e: Evaluated) -> bool:
    allowed = set(e.case.expect.channels_only)
    return all(r.channel is not None and r.channel in allowed for r in strategy(e).recommendations)


def each_cites(e: Evaluated) -> bool:
    prefixes = tuple(e.case.expect.each_cites_prefix)
    return all(
        any(evidence.id.startswith(prefixes) for evidence in r.evidence)
        for r in strategy(e).recommendations
    )


def niche_signals(e: Evaluated) -> bool:
    """The niche rule, as post-validation applies it (strategy-agent spec), on the final set."""
    cited = [e.fixture.record(ev.id) for rec in strategy(e).recommendations for ev in rec.evidence]
    competitors = collect_activity_competitors(cited)
    return not any(
        niche_problems(rec, f"recommendation {rec.ordinal}", competitors)
        for rec in strategy(e).recommendations
        if rec.kind != "MONITOR"
    )


def has_strategy_recommendations(e: Evaluated) -> bool:
    return isinstance(e.output, StrategyOutput) and bool(e.output.recommendations)


def implications(e: Evaluated) -> bool:
    count, expect = len(strategy(e).implications), e.case.expect
    low = expect.implications_min is None or count >= expect.implications_min
    return low and (expect.implications_max is None or count <= expect.implications_max)


def skills(e: Evaluated) -> bool:
    assert e.output is not None
    used = e.spec.skills_used(e.output)
    wanted = e.case.expect.skills_any
    return used <= e.spec.skill_allowlist and (not wanted or bool(used & set(wanted)))


def status_in(e: Evaluated) -> bool:
    return getattr(e.output, "status", None) in e.case.expect.status


def deliverable_shape(e: Evaluated) -> bool:
    expect, deliverable = e.case.expect.deliverable, execution(e).deliverable
    assert expect is not None
    if deliverable is None:
        return False
    body, words = deliverable.body_markdown, len(deliverable.body_markdown.split())
    checks = [
        expect.type is None or deliverable.type == expect.type,
        expect.channel is None or deliverable.channel == expect.channel,
        expect.max_chars is None or len(body) <= expect.max_chars,
        expect.min_words is None or words >= expect.min_words,
        expect.max_words is None or words <= expect.max_words,
        not expect.first_person or bool(FIRST_PERSON.search(body)),
        expect.author_persona_includes is None
        or expect.author_persona_includes in (deliverable.author_persona or ""),
        expect.images_min is None or len(deliverable.image_suggestions) >= expect.images_min,
        expect.images_max is None or len(deliverable.image_suggestions) <= expect.images_max,
    ]
    return all(checks)


def source_texts(e: Evaluated) -> list[str]:
    """The trigger activity and every activity the run retrieved (what must not be copied)."""
    run = e.record.run
    ids = {str(run.trigger.get("ref_id", ""))} if run and run.trigger else set()
    ids |= set(e.record.retrieved_ids)
    records = [r for i in sorted(ids) if i.startswith("act_") and (r := e.fixture.record(i))]
    return [text for record in records for text in activity_texts(record)]


def known_ids(e: Evaluated) -> set[str]:
    """Fixture records, plus the run's resolved trigger: a recommendation seeded from the
    case's session history is real, but lives only in the eval database."""
    run = e.record.run
    trigger = {str(run.trigger["ref_id"])} if run and run.trigger.get("ref_id") else set()
    return e.fixture.ids() | trigger


def has_deliverable(e: Evaluated) -> bool:
    return isinstance(e.output, ExecutionOutput) and e.output.deliverable is not None


def originality(e: Evaluated) -> bool:
    deliverable = execution(e).deliverable
    assert deliverable is not None
    body = deliverable.body_markdown
    for source in source_texts(e):
        similarity = jaccard(body, source)
        if longest_shared_run(body, source) > MAX_SHARED_RUN:
            return False
        if similarity is not None and similarity >= MAX_JACCARD:
            return False
    return True


def competitor_naming(e: Evaluated) -> bool:
    deliverable = execution(e).deliverable
    assert deliverable is not None
    names = [c.name for c in e.fixture.competitors]
    text = f"{deliverable.title}\n{deliverable.body_markdown}"
    return not named_competitors(text, names, e.case.input.message)


def is_create_similar(e: Evaluated) -> bool:
    trigger = e.case.input.trigger
    return (
        has_deliverable(e)
        and trigger is not None
        and (trigger.action is TriggerAction.CREATE_SIMILAR)
    )


def proposed_actions(e: Evaluated) -> bool:
    proposed = {a.action_type for a in execution(e).proposed_actions}
    return bool(proposed & set(e.case.expect.proposed_actions_any))


def route_correct(e: Evaluated) -> bool | None:
    route, run = e.case.expect.route, e.record.run
    if route is None or e.case.input.trigger is None or run is None:
        return None  # chat routing is the Step 6 classifier's job
    return (run.agent, run.intent) == (route.agent, route.intent)


def budget(e: Evaluated) -> bool:
    run = e.record.run
    skill_loads = len(run.skills_loaded) if run else 0
    # A cached repeat (agents/common/mcp.py) never reached the MCP, so it spends no budget.
    calls = sum(not c.get("cached") for c in run.tool_calls) if run else 0
    return calls <= e.case.expect.max_tool_calls and skill_loads <= MAX_LOADS_PER_RUN


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
    # §5.1: called before output and at most once. Order within the first turn is not
    # checked: parallel tool calls complete in any order.
    # Exactly one server call; a cached repeat (agents/common/mcp.py) costs nothing (owner
    # decision 2026-10-04).
    "company_context_first": needs_output(
        lambda e: (
            e.record.run is not None
            and sum(
                c["tool"] == "get_company_context" and not c.get("cached")
                for c in e.record.run.tool_calls
            )
            == 1
        )
    ),
    "evidence_grounded": needs_output(
        lambda e: e.cited <= set(e.record.retrieved_ids) and e.cited <= known_ids(e)
    ),
    "evidence_required_all": when(
        lambda e: e.case.expect.evidence_required_all,
        needs_output(lambda e: set(e.case.expect.evidence_required_all) <= e.cited),
    ),
    "evidence_required_any": when(
        lambda e: e.case.expect.evidence_required_any,
        needs_output(lambda e: bool(set(e.case.expect.evidence_required_any) & e.cited)),
    ),
    "retrieved_any": when(
        lambda e: e.case.expect.retrieved_any,
        needs_output(
            lambda e: bool(set(e.case.expect.retrieved_any) & set(e.record.retrieved_ids))
        ),
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
    "data_gaps": when(lambda e: e.case.expect.data_gaps_any, needs_output(data_gaps)),
    "channels": when(lambda e: e.case.expect.channels_only, needs_output(channels)),
    "each_cites": when(lambda e: e.case.expect.each_cites_prefix, needs_output(each_cites)),
    "niche_signals": when(has_strategy_recommendations, niche_signals),
    "implications": when(
        lambda e: (
            e.case.expect.implications_min is not None or e.case.expect.implications_max is not None
        ),
        needs_output(implications),
    ),
    "deliverable_shape": when(lambda e: e.case.expect.deliverable, needs_output(deliverable_shape)),
    "originality": when(has_deliverable, originality),
    "competitor_naming": when(is_create_similar, competitor_naming),
    "proposed_actions_any": when(
        lambda e: e.case.expect.proposed_actions_any, needs_output(proposed_actions)
    ),
    "budget": budget,
}


def run_checks(case: GoldenCase, record: RunRecord, fixture: FixtureBundle) -> dict[str, bool]:
    """Applicable check results; a run that never started fails schema_valid."""
    evaluated = evaluate_inputs(case, record, fixture)
    results = {name: check(evaluated) for name, check in CHECKS.items()}
    return {name: result for name, result in results.items() if result is not None}
