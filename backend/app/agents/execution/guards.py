"""Code-side quality and policy guards behind the agent's own check (agents-spec §7.3).

Hard problems fail the run if the one repair does not fix them; soft problems survive as a
FLAG on the quality check (design D4).
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from app.agents.common.context import RunContext
from app.agents.common.errors import UnoriginalOutputError
from app.agents.common.intents import Intent
from app.agents.execution.output import ExecutionDeliverable, ExecutionOutput
from app.intelligence.models import Channel, Competitor, CompetitorActivity, DeliverableType

MAX_SHARED_RUN = 11  # a shared run of 12 or more consecutive words is a copy
MAX_JACCARD = 0.15
NGRAM = 5
# Too few source 5-grams make Jaccard noise; only the shared-run rule applies then.
MIN_SOURCE_NGRAMS = 5
MIN_ALIAS_CHARS = 4

WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
# Presence only: counting "I" would penalise good first person (design D8). An accepted
# exception to conventions §4: a soft hint that only FLAGs, never a pass/fail gate.
FIRST_PERSON = re.compile(r"\b(?:I|I'm|I've|I'd|[Mm]y|[Mm]e)\b")
# "It's not X, it's Y" and its close cousins, including "X is not Y. It is Z" and
# "isn't to X, it's to Y" (the model dodges the literal "it's...it's" example by
# rewording the same reversal) (design D12 gap 1: machine-sounding voice).
REVERSAL = re.compile(
    r"\b(?:it'?s\s+not|is\s+not|isn'?t)\b[^\n]{0,70}\b(?:it'?s|it\s+is)\b", re.IGNORECASE
)
# Three consecutive sentences opening with the same question word ("Can X? Can Y?
# Can Z?") is the rhetorical-triplet tell, independent of the actual content.
REFLEXIVE_QUESTION = re.compile(r"\b([A-Z][a-z]+)\b[^?!.]{0,100}\?")
# The same bolded "Label:" reused as every section's closer is a template tell, not a
# one-off styling choice (e.g. "**Practical takeaway:**" after every blog H2).
BOLD_LABEL = re.compile(r"\*\*([^*\n]{2,40}):\*\*")
MIN_SAMPLE_LINE_WORDS = 3  # a one- or two-word sample fragment would over-match

QualityField = Literal["originality", "channel_fit", "brand_voice"]


@dataclass(frozen=True)
class GuardProblem:
    check: QualityField
    message: str
    hard: bool = False  # most new checks are soft; a hard one passes it explicitly


@dataclass(frozen=True)
class GuardInputs:
    """What the guards compare a deliverable with, gathered from the run."""

    intent: Intent
    message: str | None
    sources: tuple[str, ...]  # competitor texts the deliverable must not copy
    competitor_names: tuple[str, ...]
    sample_copy: tuple[str, ...] = ()  # the brand's own voice samples; never reused verbatim


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def longest_shared_run(text: str, source: str) -> int:
    """The longest run of consecutive words the two texts share."""
    a, b = words(text), words(source)
    best, previous = 0, [0] * (len(b) + 1)
    for word in a:
        current = [0] * (len(b) + 1)
        for j, other in enumerate(b, start=1):
            if word == other:
                current[j] = previous[j - 1] + 1
                best = max(best, current[j])
        previous = current
    return best


def ngrams(tokens: list[str], n: int = NGRAM) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(text: str, source: str) -> float | None:
    """5-gram Jaccard similarity, or None when the source is too short to measure."""
    ours, theirs = ngrams(words(text)), ngrams(words(source))
    if len(theirs) < MIN_SOURCE_NGRAMS:
        return None
    return len(ours & theirs) / len(ours | theirs)


def originality_problems(body: str, sources: Iterable[str]) -> list[GuardProblem]:
    problems: list[GuardProblem] = []
    for source in sources:
        run = longest_shared_run(body, source)
        if run > MAX_SHARED_RUN:
            problems.append(
                GuardProblem(
                    "originality",
                    f"the body repeats a {run}-word run from a competitor's text",
                    hard=True,
                )
            )
        similarity = jaccard(body, source)
        if similarity is not None and similarity >= MAX_JACCARD:
            problems.append(
                GuardProblem(
                    "originality",
                    f"the body is too close to a competitor's text "
                    f"(5-gram overlap {similarity:.2f})",
                    hard=True,
                )
            )
    return problems


@dataclass(frozen=True)
class Limit:
    max_chars: int | None = None
    min_words: int | None = None
    max_words: int | None = None


LIMITS: dict[DeliverableType, Limit] = {
    DeliverableType.LINKEDIN_POST: Limit(max_chars=3000),
    DeliverableType.CEO_POST: Limit(max_chars=3000),
    DeliverableType.X_POST: Limit(max_chars=280),
    DeliverableType.BLOG_DRAFT: Limit(min_words=800, max_words=1500),
}


def on_x(deliverable: ExecutionDeliverable) -> bool:
    return deliverable.type is DeliverableType.X_POST or deliverable.channel is Channel.X


def effective_limit(deliverable: ExecutionDeliverable) -> Limit:
    """The type's limit (X's for anything posted there), narrowed by what the user asked
    for: their word range replaces the default one, and their character cap only tightens."""
    base = LIMITS[DeliverableType.X_POST] if on_x(deliverable) else LIMITS.get(deliverable.type)
    base = base or Limit()
    asked = deliverable.requested_length
    if asked is None:
        return base
    # Any length the user gave replaces the default word range, so a character cap
    # never fights a default word minimum.
    caps = [cap for cap in (base.max_chars, asked.max_chars) if cap is not None]
    stated = (asked.min_words, asked.max_words, asked.max_chars) != (None, None, None)
    return Limit(
        max_chars=min(caps, default=None),
        min_words=asked.min_words if stated else base.min_words,
        max_words=asked.max_words if stated else base.max_words,
    )


def posts(deliverable: ExecutionDeliverable) -> list[str]:
    """Each text that must fit the character cap: an X thread (only when the user asked for
    one) post by post, and every variant, since any of them may be the one published."""
    body = deliverable.body_markdown
    asked = deliverable.requested_length
    if on_x(deliverable) and asked is not None and asked.thread:
        thread = [post for post in re.split(r"\n\s*\n", body) if post.strip()]
        return [*thread, *deliverable.variants]
    return [body, *deliverable.variants]


def length_problems(deliverable: ExecutionDeliverable) -> list[str]:
    limit = effective_limit(deliverable)
    problems: list[str] = []
    if limit.max_chars is not None:
        longest = max(len(post) for post in posts(deliverable))
        if longest > limit.max_chars:
            problems.append(
                f"a {deliverable.type} is at most {limit.max_chars} characters per post; "
                f"one has {longest}"
            )
    count = len(deliverable.body_markdown.split())
    low, high = limit.min_words, limit.max_words
    if (low is not None and count < low) or (high is not None and count > high):
        wanted = f"{low or 0}-{high}" if high is not None else f"at least {low}"
        problems.append(f"this {deliverable.type} should be {wanted} words; it has {count}")
    return problems


def aliases(name: str) -> set[str]:
    """The full name and its first word ("Lyfe" for "Lyfe Marketing"), when distinctive."""
    first = name.split()[0].strip(".,")
    return {name, first} if len(first) >= MIN_ALIAS_CHARS else {name}


def named_competitors(text: str, names: Iterable[str], message: str | None) -> list[str]:
    """Competitors the text names that the user's message did not ask about."""
    asked = (message or "").lower()
    found = []
    for name in names:
        forms = aliases(name)
        if any(form.lower() in asked for form in forms):
            continue
        if any(re.search(rf"\b{re.escape(form)}\b", text, re.IGNORECASE) for form in forms):
            found.append(name)
    return found


def voice_problems(body: str, sample_copy: Iterable[str]) -> list[GuardProblem]:
    """Soft machine-voice tells code can actually catch (design D12 gap 1); everything
    subtler ("sound like a person") stays the model's own job, checked by the judge."""
    problems: list[GuardProblem] = []
    if REVERSAL.search(body):
        problems.append(
            GuardProblem(
                "brand_voice",
                'avoid "X is not A, it is B" reversals in any wording - say the thing '
                "plainly instead of setting up a straw man to knock down",
            )
        )
    starts = REFLEXIVE_QUESTION.findall(body)
    if any(starts[i] == starts[i + 1] == starts[i + 2] for i in range(len(starts) - 2)):
        problems.append(
            GuardProblem(
                "brand_voice",
                "three consecutive questions open with the same word - a rhetorical "
                "triplet; cut to one strong question or make each genuinely different",
            )
        )
    labels = [label.strip().lower() for label in BOLD_LABEL.findall(body)]
    if len(labels) != len(set(labels)):
        problems.append(
            GuardProblem(
                "brand_voice",
                "the same bolded label closes more than one section - a template tell; "
                "vary each section's close instead of repeating a formula",
            )
        )
    for line in sample_copy:
        if len(words(line)) >= MIN_SAMPLE_LINE_WORDS and line.strip().lower() in body.lower():
            problems.append(
                GuardProblem(
                    "brand_voice", f'reuses the brand\'s own sample line verbatim: "{line}"'
                )
            )
    return problems


def guard_problems(deliverable: ExecutionDeliverable, inputs: GuardInputs) -> list[GuardProblem]:
    problems = [  # a variant may be the one published, so it must be original too
        problem
        for text in (deliverable.body_markdown, *deliverable.variants)
        for problem in originality_problems(text, inputs.sources)
    ]
    problems += [
        GuardProblem("channel_fit", text, hard=False) for text in length_problems(deliverable)
    ]
    if deliverable.type is DeliverableType.CEO_POST and not FIRST_PERSON.search(
        deliverable.body_markdown
    ):
        problems.append(
            GuardProblem(
                "channel_fit",
                "a CEO_POST speaks in the first person as the spokesperson, but this one "
                "never says I, me or my",
                hard=False,
            )
        )
    if inputs.intent is Intent.CREATE_SIMILAR:
        text = f"{deliverable.title}\n{deliverable.body_markdown}"
        problems += [
            GuardProblem(
                "originality",
                f"it names the competitor {name}, which the user did not ask for",
                hard=False,
            )
            for name in named_competitors(text, inputs.competitor_names, inputs.message)
        ]
    problems += [
        problem
        for text in (deliverable.body_markdown, *deliverable.variants)
        for problem in voice_problems(text, inputs.sample_copy)
    ]
    return problems


def flag(output: ExecutionOutput, problems: list[GuardProblem]) -> ExecutionOutput:
    """Soft problems the repair left: never PASS what code found failing (agents-spec §7.3)."""
    soft = [p for p in problems if not p.hard]
    check = output.quality_check
    if not soft or check is None:
        return output
    update: dict[str, object] = {p.check: "FLAG" for p in soft}
    update["notes"] = [*check.notes, *(p.message for p in soft)]
    return output.model_copy(update={"quality_check": check.model_copy(update=update)})


def ensure_original(problems: list[GuardProblem]) -> None:
    if hard := [p.message for p in problems if p.hard]:
        raise UnoriginalOutputError(
            "The draft still copies a competitor; no copy is returned", {"problems": hard}
        )


def activity_texts(record: Mapping[str, object]) -> list[str]:
    return [str(record[key]) for key in ("title", "content_excerpt") if record.get(key)]


def walk(payload: object) -> Iterable[Mapping[str, object]]:
    if isinstance(payload, Mapping):
        yield payload
        for value in payload.values():
            yield from walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk(item)


def guard_inputs(context: RunContext, message: str | None) -> GuardInputs:
    """Sources and names from the trigger and the run's MCP results; no extra reads."""
    records = [*walk(context.trigger_context or {}), *walk(context.tool_results)]
    activities = [
        r for r in records if str(r.get("id", "")).startswith(CompetitorActivity.id_prefix)
    ]
    sources = dict.fromkeys(text for r in activities for text in activity_texts(r))
    names = {str(r["competitor_name"]) for r in activities if r.get("competitor_name")}
    names |= {
        str(r["name"]) for r in records if str(r.get("id", "")).startswith(Competitor.id_prefix)
    }
    # get_company_context returns the full Company record; brand_voice (and its
    # sample_copy) is a nested Mapping, so walk() already surfaces it directly.
    sample_copy: tuple[str, ...] = ()
    for r in records:
        candidate = r.get("sample_copy")
        if isinstance(candidate, list):
            sample_copy = tuple(str(line) for line in candidate)
            break
    return GuardInputs(
        intent=context.intent,
        message=message,
        sources=tuple(sources),
        competitor_names=tuple(sorted(names)),
        sample_copy=sample_copy,
    )
