"""Code-side quality and policy guards behind the agent's own check (agents-spec §7.3).

Hard problems fail the run if the one repair does not fix them; soft problems survive as a
FLAG on the quality check (design D4).
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from app.agents.common.context import RunContext
from app.agents.common.intents import Intent
from app.agents.execution.output import ExecutionDeliverable
from app.core.errors import DomainError
from app.intelligence.models import DeliverableType

MAX_SHARED_RUN = 11  # a shared run of 12 or more consecutive words is a copy
MAX_JACCARD = 0.15
NGRAM = 5
# Too few source 5-grams make Jaccard noise; only the shared-run rule applies then.
MIN_SOURCE_NGRAMS = 5
MIN_ALIAS_CHARS = 4

WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
# "a 500-word blog", "300 words" or "1,200 to 1,500 words": the user set the length.
USER_LENGTH = re.compile(r"\d[\d,]*\s*-?\s*words?\b", re.IGNORECASE)
THREAD = re.compile(r"\bthread\b", re.IGNORECASE)

QualityField = Literal["originality", "channel_fit"]


class UnoriginalOutputError(DomainError):
    """The deliverable still copies its source after the repair; no copy is returned."""

    code = "UNORIGINAL_OUTPUT"


@dataclass(frozen=True)
class GuardProblem:
    check: QualityField
    message: str
    hard: bool


@dataclass(frozen=True)
class GuardInputs:
    """What the guards compare a deliverable with, gathered from the run."""

    intent: Intent
    message: str | None
    sources: tuple[str, ...]  # competitor texts the deliverable must not copy
    competitor_names: tuple[str, ...]


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
                    f"the body repeats a {run}-word run from the source; rewrite it in "
                    "your own words and take a different angle",
                    hard=True,
                )
            )
        similarity = jaccard(body, source)
        if similarity is not None and similarity >= MAX_JACCARD:
            problems.append(
                GuardProblem(
                    "originality",
                    f"the body is too close to the source (5-gram overlap {similarity:.2f}); "
                    "take a different angle and structure",
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


def x_posts(body: str, message: str | None) -> list[str]:
    """An X thread (only when asked for) is checked post by post: one per paragraph."""
    if message and THREAD.search(message):
        return [post for post in re.split(r"\n\s*\n", body) if post.strip()]
    return [body]


def length_problems(deliverable: ExecutionDeliverable, message: str | None) -> list[str]:
    limit = LIMITS.get(deliverable.type)
    if limit is None:
        return []
    body = deliverable.body_markdown
    problems: list[str] = []
    if limit.max_chars is not None:
        posts = x_posts(body, message) if deliverable.type is DeliverableType.X_POST else [body]
        longest = max(len(post) for post in posts)
        if longest > limit.max_chars:
            problems.append(
                f"a {deliverable.type} is at most {limit.max_chars} characters per post; "
                f"one has {longest}"
            )
    # A length the user gave overrides the default word range.
    if limit.min_words is not None and not (message and USER_LENGTH.search(message)):
        count = len(body.split())
        if not limit.min_words <= count <= (limit.max_words or count):
            problems.append(
                f"a {deliverable.type} is {limit.min_words}-{limit.max_words} words; "
                f"this one has {count}"
            )
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


def guard_problems(deliverable: ExecutionDeliverable, inputs: GuardInputs) -> list[GuardProblem]:
    problems = originality_problems(deliverable.body_markdown, inputs.sources)
    problems += [
        GuardProblem("channel_fit", text, hard=False)
        for text in length_problems(deliverable, inputs.message)
    ]
    if inputs.intent is Intent.CREATE_SIMILAR:
        text = f"{deliverable.title}\n{deliverable.body_markdown}"
        problems += [
            GuardProblem(
                "originality",
                f"do not name the competitor {name}; write about the idea, not them",
                hard=False,
            )
            for name in named_competitors(text, inputs.competitor_names, inputs.message)
        ]
    return problems


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
    activities = [r for r in records if str(r.get("id", "")).startswith("act_")]
    sources = dict.fromkeys(text for r in activities for text in activity_texts(r))
    names = {str(r["competitor_name"]) for r in activities if r.get("competitor_name")}
    names |= {str(r["name"]) for r in records if str(r.get("id", "")).startswith("cpt_")}
    return GuardInputs(
        intent=context.intent,
        message=message,
        sources=tuple(sources),
        competitor_names=tuple(sorted(names)),
    )
