"""Post-validation of StrategyOutput (agents-spec §6.2), run in code after the SDK parses it."""

from collections.abc import Mapping

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.common.intents import Intent
from app.agents.strategy.output import StrategyOutput, StrategyRecommendation

MAX_TITLE_CHARS = 90
MAX_INSIGHT_CHARS = 240
MAX_AUDIENCE_CHARS = 80
MAX_NOTE_CHARS = 140


def unknown_ids(output: StrategyOutput, retrieved: set[str]) -> list[str]:
    cited = {e.id for rec in output.recommendations for e in rec.evidence}
    return sorted(cited - retrieved)


EVIDENCE_PREFIX = {"activity": "act_", "trend": "trd_", "influencer": "inf_", "company": "cmp_"}
MAX_RECOMMENDATIONS = 5
# Intents that explain without recommending, so they never replace the set.
EXPLAIN_ONLY = frozenset({Intent.WHY_IT_MATTERS})
# The niche rule (strategy-agent spec): signals from the market, not the company record.
EXTERNAL_KINDS = frozenset({"activity", "trend", "influencer"})
MIN_SIGNALS = 2


def niche_problems(
    rec: StrategyRecommendation, label: str, activity_competitors: Mapping[str, str]
) -> list[str]:
    """A non-MONITOR recommendation combines signals and names its insight and audience."""
    problems: list[str] = []
    signals = {e.id: e.kind for e in rec.evidence if e.kind in EXTERNAL_KINDS}
    if rec.evidence and len(signals) < MIN_SIGNALS:  # no evidence is reported on its own
        problems.append(
            f"{label} must combine at least {MIN_SIGNALS} distinct signals (activities, trends "
            "or influencers); the company record does not count"
        )
    # An activity whose competitor is unknown counts as its own competitor.
    elif (
        signals
        and all(kind == "activity" for kind in signals.values())
        and len({activity_competitors.get(i, i) for i in signals}) < MIN_SIGNALS
    ):
        problems.append(
            f"{label} cites activities from only one competitor; add a trend, an "
            "influencer or another competitor's move"
        )
    if not rec.insight.strip():
        problems.append(
            f"{label} needs an insight: what the signals reveal together, the white space "
            "no cited competitor occupies, and why Marketing Eye can own it"
        )
    if not rec.audience.strip():
        problems.append(f"{label} needs an audience: the specific segment it targets")
    return problems


def contract_problems(
    output: StrategyOutput,
    loaded_skills: set[str],
    activity_competitors: Mapping[str, str],
    intent: Intent,
) -> list[str]:
    """Rules the agent must fix itself: code cannot invent evidence, text or a next action."""
    problems: list[str] = []
    if output.status == "INSUFFICIENT_DATA" and output.recommendations:
        problems.append("an INSUFFICIENT_DATA answer must have no recommendations")
    if intent in EXPLAIN_ONLY and output.recommendations:
        problems.append(f"a {intent} answer explains in implications and has no recommendations")
    if len(output.recommendations) > MAX_RECOMMENDATIONS:
        problems.append(
            f"return at most {MAX_RECOMMENDATIONS} recommendations (aim for 1-3); keep the "
            "strongest and drop the rest"
        )
    for rec in output.recommendations:
        label = f"recommendation {rec.ordinal}"
        if not rec.title.strip() or not rec.rationale.strip():
            problems.append(f"{label} needs a title and a rationale")
        if not rec.evidence:
            problems.append(f"{label} cites no evidence")
        for evidence in rec.evidence:
            if not evidence.id.startswith(EVIDENCE_PREFIX[evidence.kind]):
                problems.append(f"{label}: {evidence.id} is not a {evidence.kind} ID")
            if not evidence.note.strip():
                problems.append(f"{label}: evidence {evidence.id} needs a note")
        if rec.kind != "MONITOR" and (rec.next_action is None or not rec.next_action.brief.strip()):
            problems.append(f"{label} ({rec.kind}) needs a next_action with a brief")
        if rec.kind != "MONITOR":
            problems += niche_problems(rec, label, activity_competitors)
        if unloaded := sorted(set(rec.skills_used) - loaded_skills):
            problems.append(f"{label} lists skills you did not load: {', '.join(unloaded)}")
    return problems


def repair_message(unknown: list[str], problems: list[str]) -> str:
    lines = [
        "Your answer broke the output contract. Fix it and return StrategyOutput again. "
        "Your earlier tool results still count; do not call get_company_context again."
    ]
    if unknown:
        lines.append(
            f"These IDs were not retrieved in this run: {', '.join(unknown)}. "
            "Cite only IDs a tool returned, or retrieve the evidence first."
        )
    lines += problems
    return "\n".join(lines)


def ensure_valid(
    output: StrategyOutput,
    retrieved: set[str],
    loaded_skills: set[str],
    activity_competitors: Mapping[str, str],
    intent: Intent,
) -> None:
    if unknown := unknown_ids(output, retrieved):
        raise UngroundedOutputError("Cited evidence was not retrieved", {"ids": unknown})
    if problems := contract_problems(output, loaded_skills, activity_competitors, intent):
        raise InvalidOutputError("; ".join(problems))


def normalise(output: StrategyOutput) -> StrategyOutput:
    """Fixes code can make safely: ordinals 1..n in the given order, and length caps."""
    recommendations = [
        rec.model_copy(
            update={
                "ordinal": index,
                "title": rec.title[:MAX_TITLE_CHARS],
                "insight": rec.insight.strip()[:MAX_INSIGHT_CHARS],
                "audience": rec.audience.strip()[:MAX_AUDIENCE_CHARS],
                "evidence": [
                    e.model_copy(update={"note": e.note[:MAX_NOTE_CHARS]}) for e in rec.evidence
                ],
            }
        )
        for index, rec in enumerate(output.recommendations, start=1)
    ]
    return output.model_copy(update={"recommendations": recommendations})
