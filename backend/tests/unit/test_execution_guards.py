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
from app.intelligence.models import Channel, DeliverableType, RequestedLength
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


def asking(
    min_words: int | None = None,
    max_words: int | None = None,
    max_chars: int | None = None,
    thread: bool = False,
) -> dict[str, object]:
    return {
        "requested_length": RequestedLength(
            min_words=min_words, max_words=max_words, max_chars=max_chars, thread=thread
        )
    }


def test_channel_limits() -> None:
    long_post = deliverable(DeliverableType.LINKEDIN_POST, body="x" * 3001)
    assert "at most 3000 characters" in length_problems(long_post)[0]
    tweet = deliverable(DeliverableType.X_POST, body="y" * 281)
    assert length_problems(tweet)
    thread = deliverable(DeliverableType.X_POST, body=f"{'a' * 200}\n\n{'b' * 200}")
    assert length_problems(thread.model_copy(update=asking(thread=True))) == []
    assert length_problems(thread)  # one post, 402 characters
    long_variant = deliverable(DeliverableType.X_POST, body="Short.")
    assert length_problems(long_variant.model_copy(update={"variants": ["z" * 300]}))


def test_the_user_length_replaces_the_default_and_is_enforced() -> None:
    short_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 300)
    assert "800-1500 words" in length_problems(short_blog)[0]
    assert length_problems(short_blog.model_copy(update=asking(250, 350))) == []
    good_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 900)
    assert length_problems(good_blog) == []
    long_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 643)
    assert "450-550 words" in length_problems(long_blog.model_copy(update=asking(450, 550)))[0]
    assert length_problems(short_blog.model_copy(update=asking()))  # nothing stated
    capped_blog = deliverable(DeliverableType.BLOG_DRAFT, body="word " * 300)
    assert length_problems(capped_blog.model_copy(update=asking(max_chars=1999))) == []
    thread = deliverable(DeliverableType.X_POST, body=f"{'a' * 200}\n\n{'b' * 200}")
    thread = thread.model_copy(update=asking(thread=True) | {"variants": ["v" * 900]})
    assert length_problems(thread)  # a variant still fits the cap in a thread
    post = deliverable(DeliverableType.X_POST, body="y" * 240)
    assert "at most 200" in length_problems(post.model_copy(update=asking(max_chars=200)))[0]
    assert length_problems(post.model_copy(update=asking(max_chars=500))) == []  # X cap holds


def test_a_copied_variant_is_a_hard_problem() -> None:
    item = deliverable(body=OWN).model_copy(update={"variants": [SOURCE]})
    assert any(p.hard for p in guard_problems(item, inputs()))


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


def test_a_ceo_post_must_speak_in_the_first_person() -> None:
    impersonal = deliverable(DeliverableType.CEO_POST, body="Positioning is never finished.")
    problems = guard_problems(impersonal, inputs(Intent.CHAT))
    assert [(p.check, p.hard) for p in problems] == [("channel_fit", False)]
    personal = deliverable(DeliverableType.CEO_POST, body="My view: positioning is never done.")
    assert guard_problems(personal, inputs(Intent.CHAT)) == []


def test_a_ceo_post_on_x_keeps_to_the_x_limit() -> None:
    on_x = deliverable(DeliverableType.CEO_POST, body="My view. " * 40)  # 360 characters
    on_x = on_x.model_copy(update={"channel": Channel.X})
    assert "at most 280 characters" in length_problems(on_x)[0]
