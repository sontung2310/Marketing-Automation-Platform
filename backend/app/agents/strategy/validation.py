"""Post-validation of StrategyOutput (agents-spec §6.2), run in code after the SDK parses it."""

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.strategy.output import StrategyOutput

MAX_TITLE_CHARS = 90
MAX_NOTE_CHARS = 140


def unknown_ids(output: StrategyOutput, retrieved: set[str]) -> list[str]:
    cited = {e.id for rec in output.recommendations for e in rec.evidence}
    return sorted(cited - retrieved)


EVIDENCE_PREFIX = {"activity": "act_", "trend": "trd_", "influencer": "inf_", "company": "cmp_"}


def contract_problems(output: StrategyOutput, loaded_skills: set[str]) -> list[str]:
    """Rules the agent must fix itself: code cannot invent evidence, text or a next action."""
    problems: list[str] = []
    if output.status == "INSUFFICIENT_DATA" and output.recommendations:
        problems.append("an INSUFFICIENT_DATA answer must have no recommendations")
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


def ensure_valid(output: StrategyOutput, retrieved: set[str], loaded_skills: set[str]) -> None:
    if unknown := unknown_ids(output, retrieved):
        raise UngroundedOutputError("Cited evidence was not retrieved", {"ids": unknown})
    if problems := contract_problems(output, loaded_skills):
        raise InvalidOutputError("; ".join(problems))


def normalise(output: StrategyOutput) -> StrategyOutput:
    """Fixes code can make safely: ordinals 1..n in the given order, and length caps."""
    recommendations = [
        rec.model_copy(
            update={
                "ordinal": index,
                "title": rec.title[:MAX_TITLE_CHARS],
                "evidence": [
                    e.model_copy(update={"note": e.note[:MAX_NOTE_CHARS]}) for e in rec.evidence
                ],
            }
        )
        for index, rec in enumerate(output.recommendations, start=1)
    ]
    return output.model_copy(update={"recommendations": recommendations})
