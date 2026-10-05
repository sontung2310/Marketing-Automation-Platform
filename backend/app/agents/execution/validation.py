"""Post-validation of ExecutionOutput (agents-spec §7.2), run in code after the SDK parses it."""

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.execution.output import ExecutionDeliverable, ExecutionOutput
from app.intelligence.models import ActionType, DeliverableType

MAX_ACTIONS = 2
MAX_VARIANTS = 3

_SOCIAL = frozenset({ActionType.SCHEDULE_SOCIAL_POST, ActionType.ADD_TO_CONTENT_CALENDAR})
_CMS = frozenset({ActionType.CREATE_CMS_DRAFT, ActionType.ADD_TO_CONTENT_CALENDAR})
_EMAIL = frozenset({ActionType.CREATE_EMAIL_DRAFT, ActionType.ADD_TO_CONTENT_CALENDAR})
# The actions that fit each deliverable (the instructions' table).
ACTIONS_FOR: dict[DeliverableType, frozenset[ActionType]] = {
    DeliverableType.LINKEDIN_POST: _SOCIAL,
    DeliverableType.X_POST: _SOCIAL,
    DeliverableType.INSTAGRAM_POST: _SOCIAL,
    DeliverableType.CEO_POST: _SOCIAL,
    DeliverableType.BLOG_DRAFT: _CMS,
    DeliverableType.BLOG_OUTLINE: _CMS,
    DeliverableType.EMAIL: _EMAIL,
    DeliverableType.INFLUENCER_OUTREACH: _EMAIL,
    DeliverableType.AD_COPY: frozenset({ActionType.ADD_TO_CONTENT_CALENDAR}),
    DeliverableType.RESPONSE_BRIEF: frozenset({ActionType.ADD_TO_CONTENT_CALENDAR}),
}

_ONE = (1, 1)
_NONE = (0, 0)
# How many image suggestions each deliverable carries, as (min, max) (design D11).
IMAGES_FOR: dict[DeliverableType, tuple[int, int]] = {
    DeliverableType.LINKEDIN_POST: _ONE,
    DeliverableType.X_POST: _ONE,
    DeliverableType.INSTAGRAM_POST: _ONE,
    DeliverableType.CEO_POST: _ONE,
    DeliverableType.AD_COPY: _ONE,
    DeliverableType.BLOG_DRAFT: (1, 2),
    DeliverableType.BLOG_OUTLINE: (1, 2),
    DeliverableType.EMAIL: _NONE,
    DeliverableType.INFLUENCER_OUTREACH: _NONE,
    DeliverableType.RESPONSE_BRIEF: _NONE,
}


def image_problem(deliverable: ExecutionDeliverable) -> str | None:
    low, high = IMAGES_FOR[deliverable.type]
    count = len(deliverable.image_suggestions)
    if low <= count <= high:
        return None
    wanted = str(low) if low == high else f"{low}-{high}"
    return f"a {deliverable.type} carries {wanted} image_suggestions, not {count}"


def unknown_ids(output: ExecutionOutput, retrieved: set[str]) -> list[str]:
    return sorted(set(output.evidence_ids) - retrieved)


def contract_problems(
    output: ExecutionOutput, expected: DeliverableType | None, loaded_skills: set[str]
) -> list[str]:
    """Rules the agent must fix itself: code cannot write the deliverable for it."""
    problems: list[str] = []
    deliverable = output.deliverable
    if output.status == "OK":
        if deliverable is None or output.quality_check is None:
            problems.append("an OK answer needs a deliverable and a quality_check")
        if len(output.proposed_actions) > MAX_ACTIONS:
            problems.append(f"propose at most {MAX_ACTIONS} actions")
    elif deliverable is not None or output.proposed_actions:
        problems.append(f"a {output.status} answer has no deliverable and no proposed actions")
    if deliverable is not None:
        if expected is not None and deliverable.type is not expected:
            problems.append(f"the deliverable must be a {expected}, not a {deliverable.type}")
        if not deliverable.title.strip() or not deliverable.body_markdown.strip():
            problems.append("the deliverable needs a title and a body")
        if len(deliverable.variants) > MAX_VARIANTS:
            problems.append(f"give at most {MAX_VARIANTS} variants")
        if unfit := sorted(
            {a.action_type for a in output.proposed_actions} - ACTIONS_FOR[deliverable.type]
        ):
            problems.append(
                f"{', '.join(unfit)} does not fit a {deliverable.type}; propose only "
                f"{', '.join(sorted(ACTIONS_FOR[deliverable.type]))}"
            )
        if problem := image_problem(deliverable):
            problems.append(problem)
        if deliverable.type is DeliverableType.CEO_POST and not deliverable.author_persona:
            problems.append("a CEO_POST names its author_persona (the company spokesperson)")
    if output.status == "NEEDS_CLARIFICATION" and not output.clarification_options:
        problems.append("a clarification gives 2-3 clarification_options")
    if unloaded := sorted(set(output.skills_used) - loaded_skills):
        problems.append(f"skills_used lists skills you did not load: {', '.join(unloaded)}")
    return problems


def repair_message(unknown: list[str], problems: list[str]) -> str:
    lines = [
        "Your answer broke the output contract. Fix it and return ExecutionOutput again. "
        "Your earlier tool results still count; do not call get_company_context again."
    ]
    if unknown:
        lines.append(
            f"These IDs were not retrieved in this run: {', '.join(unknown)}. "
            "List only IDs a tool returned in evidence_ids, or retrieve the evidence first."
        )
    lines += problems
    return "\n".join(lines)


def ensure_valid(
    output: ExecutionOutput,
    retrieved: set[str],
    expected: DeliverableType | None,
    loaded_skills: set[str],
) -> None:
    if unknown := unknown_ids(output, retrieved):
        raise UngroundedOutputError("Cited evidence was not retrieved", {"ids": unknown})
    if problems := contract_problems(output, expected, loaded_skills):
        raise InvalidOutputError("; ".join(problems))


def word_count(text: str) -> int:
    return len(text.split())


def normalise(output: ExecutionOutput) -> ExecutionOutput:
    """Fixes code can make safely: the real word count."""
    if output.deliverable is None:
        return output
    deliverable = output.deliverable.model_copy(
        update={"word_count": word_count(output.deliverable.body_markdown)}
    )
    return output.model_copy(update={"deliverable": deliverable})
