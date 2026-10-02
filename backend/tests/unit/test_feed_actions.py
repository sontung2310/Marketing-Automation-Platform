from datetime import UTC, datetime

import pytest

from app.core.errors import ValidationError
from app.intelligence.models import ActivityType, AgentName, Channel, DeliverableType
from app.orchestration.feed import ACTIVITY_ACTIONS, ItemActionName, decode_cursor

EXECUTION_TYPES = {ActivityType.NEW_BLOG, ActivityType.SOCIAL_POST, ActivityType.EXECUTIVE_POST}


@pytest.mark.parametrize("activity_type", list(ActivityType))
def test_every_activity_type_has_one_primary_action_per_specs_6(
    activity_type: ActivityType,
) -> None:
    actions = ACTIVITY_ACTIONS[activity_type](Channel.LINKEDIN)

    assert [action.primary for action in actions].count(True) == 1
    if activity_type in EXECUTION_TYPES:
        assert [a.action for a in actions] == [
            ItemActionName.CREATE_SIMILAR,
            ItemActionName.WHY_IT_MATTERS,
        ]
        assert actions[0].agent is AgentName.EXECUTION
    else:
        assert [(a.action, a.label, a.agent) for a in actions] == [
            (ItemActionName.RESPONSE_PLAN, "Plan a response", AgentName.STRATEGY)
        ]


@pytest.mark.parametrize(
    ("channel", "deliverable"),
    [
        (Channel.LINKEDIN, DeliverableType.LINKEDIN_POST),
        (Channel.X, DeliverableType.X_POST),
        (Channel.INSTAGRAM, DeliverableType.INSTAGRAM_POST),
    ],
)
def test_social_post_stays_on_its_channel(channel: Channel, deliverable: DeliverableType) -> None:
    assert ACTIVITY_ACTIONS[ActivityType.SOCIAL_POST](channel)[0].deliverable_type is deliverable


def test_executive_post_drafts_a_ceo_post() -> None:
    primary = ACTIVITY_ACTIONS[ActivityType.EXECUTIVE_POST](Channel.LINKEDIN)[0]
    assert (primary.label, primary.deliverable_type) == (
        "Draft a CEO post",
        DeliverableType.CEO_POST,
    )


def test_garbage_cursor_is_a_validation_error() -> None:
    with pytest.raises(ValidationError):
        decode_cursor("not-a-cursor")
    assert decode_cursor("MjAyNi0xMC0wMlQwMDowMDowMCswMDowMHxhY3RfMQ==") == (
        datetime(2026, 10, 2, tzinfo=UTC),
        "act_1",
    )
