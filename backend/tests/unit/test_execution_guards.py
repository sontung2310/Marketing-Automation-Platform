"""Execution guards: originality, channel length and competitor naming (agents-spec §7.3)."""

from app.agents.common.context import RunContext
from app.agents.common.intents import Intent
from app.agents.execution.guards import (
    GuardInputs,
    guard_inputs,
    guard_problems,
    jaccard,
    length_problems,
    longest_shared_run,
    named_competitors,
)
from app.intelligence.models import DeliverableType
from tests.execution_samples import deliverable

SOURCE = (
    "Most B2B content calendars fail because they start with formats instead of buyers. "
    "Before you plan a single post, list the ten questions your best customers asked during "
    "their last buying cycle. Group them by stage: problem, options and decision."
)
TWELVE = "list the ten questions your best customers asked during their last buying"
ELEVEN = "list the ten questions your best customers asked during their last"
# Original prose around a borrowed phrase, as in a real post (keeps 5-gram overlap low).
OWN = (
    "Marketing Eye sees the same pattern with every growing firm we advise. Strong plans "
    "come from listening first, writing second and measuring what changes in sales "
    "conversations over the following quarter, so the work keeps earning its place."
)


def inputs(intent: Intent = Intent.CREATE_SIMILAR, message: str | None = None) -> GuardInputs:
    return GuardInputs(intent, message, (SOURCE,), ("Brightlane Marketing",))


def test_shared_run_ignores_case_and_punctuation() -> None:
    assert longest_shared_run(f"Start here. {TWELVE.upper()}!", SOURCE) == 12
    assert longest_shared_run(f"Start here: {ELEVEN}, then stop.", SOURCE) == 11


def test_a_twelve_word_copy_is_a_hard_problem() -> None:
    body = f"{OWN} We think you should {TWELVE} and then talk to sales."
    problems = guard_problems(deliverable(body=body), inputs())
    assert [(p.check, p.hard) for p in problems] == [("originality", True)]
    assert "12-word run" in problems[0].message


def test_an_eleven_word_near_copy_passes() -> None:
    body = f"{OWN} Our advice: {ELEVEN} cycle, then plan the work around those answers."
    assert guard_problems(deliverable(body=body), inputs()) == []


def test_jaccard_flags_a_reworded_copy_and_skips_short_sources() -> None:
    rearranged = SOURCE.replace("Most B2B", "Many B2B").replace("Group them", "Sort them")
    similarity = jaccard(rearranged, SOURCE)
    assert similarity is not None and similarity >= 0.15
    assert jaccard("anything at all", "Focus is a service to the team.") is None


def test_channel_limits() -> None:
    long_post = deliverable(DeliverableType.LINKEDIN_POST, body="x" * 3001)
    assert "at most 3000 characters" in length_problems(long_post, None)[0]
    tweet = deliverable(DeliverableType.X_POST, body="y" * 281)
    assert length_problems(tweet, None)
    thread = deliverable(DeliverableType.X_POST, body=f"{'a' * 200}\n\n{'b' * 200}")
    assert length_problems(thread, "Write an X thread") == []
    assert length_problems(thread, "Write an X post")  # one post, 402 characters


def test_blog_word_range_unless_the_user_set_a_length() -> None:
    short_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 300)
    assert "800-1500 words" in length_problems(short_blog, None)[0]
    assert length_problems(short_blog, "Write a 300-word blog") == []
    good_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 900)
    assert length_problems(good_blog, None) == []


def test_competitor_names_are_soft_and_only_for_create_similar() -> None:
    body = "Unlike Brightlane, we start with the buyer."
    problems = guard_problems(deliverable(body=body), inputs())
    assert [(p.check, p.hard) for p in problems] == [("originality", False)]
    assert guard_problems(deliverable(body=body), inputs(Intent.CHAT)) == []
    assert named_competitors(body, ["Brightlane Marketing"], "Compare us with Brightlane") == []
    assert named_competitors("A bright lane ahead.", ["Brightlane Marketing"], None) == []


def test_guard_inputs_come_from_the_trigger_and_tool_results() -> None:
    ctx = RunContext(
        company_id="cmp_marketing_eye",
        session_id="ses_1",
        run_id="run_1",
        intent=Intent.CREATE_SIMILAR,
        trigger_context={
            "id": "act_1",
            "title": "A guide",
            "content_excerpt": SOURCE,
            "competitor_name": "Brightlane Marketing",
        },
    )
    ctx.tool_results = [
        {"results": [{"id": "cpt_2", "name": "Kestrel Growth Co."}]},
        {"results": [{"id": "inf_1", "name": "Priya Shah"}]},  # an influencer, not a rival
    ]
    built = guard_inputs(ctx, "Make it punchy")
    assert built.sources == ("A guide", SOURCE)
    assert built.competitor_names == ("Brightlane Marketing", "Kestrel Growth Co.")
    assert built.message == "Make it punchy"
