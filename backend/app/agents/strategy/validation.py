"""Post-validation of StrategyOutput (agents-spec §6.2), run in code after the SDK parses it."""

from app.agents.strategy.output import StrategyOutput
from app.core.errors import DomainError

MAX_TITLE_CHARS = 90
MAX_NOTE_CHARS = 140


class UngroundedOutputError(DomainError):
    code = "UNGROUNDED_OUTPUT"


class InvalidOutputError(DomainError):
    code = "INVALID_OUTPUT"


def unknown_ids(output: StrategyOutput, retrieved: set[str]) -> list[str]:
    cited = {e.id for rec in output.recommendations for e in rec.evidence}
    return sorted(cited - retrieved)


def contract_problems(output: StrategyOutput) -> list[str]:
    """Rules the agent must fix itself: code cannot invent evidence or a next action."""
    problems: list[str] = []
    for rec in output.recommendations:
        if not rec.evidence:
            problems.append(f"recommendation {rec.ordinal} cites no evidence")
        if rec.kind != "MONITOR" and rec.next_action is None:
            problems.append(f"recommendation {rec.ordinal} ({rec.kind}) has no next_action")
    return problems


def repair_message(unknown: list[str], problems: list[str]) -> str:
    lines = ["Your answer broke the output contract. Fix it and return StrategyOutput again."]
    if unknown:
        lines.append(
            f"These IDs were not retrieved in this run: {', '.join(unknown)}. "
            "Cite only IDs a tool returned, or retrieve the evidence first."
        )
    lines += problems
    return "\n".join(lines)


def ensure_valid(output: StrategyOutput, retrieved: set[str]) -> None:
    if unknown := unknown_ids(output, retrieved):
        raise UngroundedOutputError("Cited evidence was not retrieved", {"ids": unknown})
    if problems := contract_problems(output):
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
