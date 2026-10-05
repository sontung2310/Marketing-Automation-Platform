"""Execution post-validation: grounding, the type, the status shape and the word count."""

import pytest

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.execution.output import ExecutionDeliverable
from app.agents.execution.validation import (
    ACTIONS_FOR,
    IMAGES_FOR,
    contract_problems,
    ensure_valid,
    normalise,
    unknown_ids,
)
from app.intelligence.models import ActionType, DeliverableType, ImageSuggestion
from tests.execution_samples import clarification, deliverable, execution_output

IMAGE = ImageSuggestion(placement="Post attachment", content="A whiteboard", style="Photo")

LOADED = {"social"}


def test_a_valid_post_has_no_problems() -> None:
    output = execution_output()
    assert unknown_ids(output, {"act_1"}) == []
    assert contract_problems(output, DeliverableType.LINKEDIN_POST, LOADED) == []


def test_wrong_type_is_a_problem() -> None:
    problems = contract_problems(execution_output(), DeliverableType.BLOG_DRAFT, LOADED)
    assert problems == ["the deliverable must be a BLOG_DRAFT, not a LINKEDIN_POST"]


def test_status_shape() -> None:
    no_deliverable = execution_output().model_copy(update={"deliverable": None})
    assert "needs a deliverable" in contract_problems(no_deliverable, None, LOADED)[0]
    asking_with_actions = clarification().model_copy(
        update={"proposed_actions": execution_output().proposed_actions}
    )
    assert "no proposed actions" in contract_problems(asking_with_actions, None, LOADED)[0]
    assert contract_problems(clarification(), None, LOADED) == []


def test_limits_skills_and_ceo_persona() -> None:
    actions = (ActionType.SCHEDULE_SOCIAL_POST,) * 3
    ceo = execution_output(deliverable(DeliverableType.CEO_POST), actions=actions)
    ceo = ceo.model_copy(update={"skills_used": ["pricing"]})
    problems = contract_problems(ceo, None, LOADED)
    assert "propose at most 2 actions" in problems
    assert any("author_persona" in p for p in problems)
    assert any("did not load: pricing" in p for p in problems)


def test_ensure_valid_raises_the_matching_error() -> None:
    with pytest.raises(UngroundedOutputError):
        ensure_valid(execution_output(evidence_ids=("act_invented",)), {"act_1"}, None, LOADED)
    with pytest.raises(InvalidOutputError):
        ensure_valid(execution_output(), {"act_1"}, DeliverableType.X_POST, LOADED)


def test_normalise_counts_words() -> None:
    output = normalise(execution_output(deliverable(body="One two three four")))
    assert output.deliverable is not None and output.deliverable.word_count == 4
    assert normalise(clarification()) == clarification()


def test_actions_must_fit_the_deliverable() -> None:
    email = execution_output(deliverable(DeliverableType.EMAIL))  # proposes a social post
    problems = contract_problems(email, None, LOADED)
    assert problems == [
        "schedule_social_post does not fit a EMAIL; propose only "
        "add_to_content_calendar, create_email_draft"
    ]
    assert set(ACTIONS_FOR) == set(DeliverableType)  # every type has its actions


def image_problems(item: ExecutionDeliverable) -> list[str]:
    output = execution_output(item, actions=())
    return [p for p in contract_problems(output, None, LOADED) if "image_suggestions" in p]


@pytest.mark.parametrize("deliverable_type", list(DeliverableType))
def test_image_suggestion_counts_per_type(deliverable_type: DeliverableType) -> None:
    low, high = IMAGES_FOR[deliverable_type]
    item = deliverable(deliverable_type)
    assert len(item.image_suggestions) == low
    assert image_problems(item) == []
    extra = item.image_suggestions + [IMAGE] * (high - low + 1)
    assert image_problems(item.model_copy(update={"image_suggestions": extra}))
    if low:
        empty = item.model_copy(update={"image_suggestions": []})
        assert image_problems(empty)[0].endswith("image_suggestions, not 0")
