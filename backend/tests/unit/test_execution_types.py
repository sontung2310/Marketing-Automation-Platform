"""Every Execution trigger fixes its deliverable type in code (specs §6)."""

import pytest

from app.agents.common.intents import Intent
from app.agents.execution.types import expected_type
from app.core.errors import ValidationError
from app.intelligence.models import DeliverableType


@pytest.mark.parametrize(
    ("activity_type", "channel", "expected"),
    [
        ("NEW_BLOG", "WEBSITE", DeliverableType.BLOG_DRAFT),
        ("SOCIAL_POST", "LINKEDIN", DeliverableType.LINKEDIN_POST),
        ("SOCIAL_POST", "X", DeliverableType.X_POST),
        ("SOCIAL_POST", "INSTAGRAM", DeliverableType.INSTAGRAM_POST),
        ("EXECUTIVE_POST", "LINKEDIN", DeliverableType.CEO_POST),
        ("EXECUTIVE_POST", "X", DeliverableType.CEO_POST),
    ],
)
def test_create_similar_follows_the_activity(
    activity_type: str, channel: str, expected: DeliverableType
) -> None:
    activity = {"id": "act_1", "activity_type": activity_type, "channel": channel}
    assert expected_type(Intent.CREATE_SIMILAR, activity) is expected


@pytest.mark.parametrize(
    ("activity_type", "channel"), [("PRICE_CHANGE", "WEBSITE"), ("SOCIAL_POST", "FACEBOOK")]
)
def test_create_similar_rejects_activities_with_no_deliverable(
    activity_type: str, channel: str
) -> None:
    activity = {"id": "act_1", "activity_type": activity_type, "channel": channel}
    with pytest.raises(ValidationError, match="no deliverable"):
        expected_type(Intent.CREATE_SIMILAR, activity)


def test_recommendation_uses_its_next_action() -> None:
    rec = {"id": "rec_1", "next_action": {"deliverable_type": "EMAIL", "brief": "Nurture"}}
    assert expected_type(Intent.FROM_RECOMMENDATION, rec) is DeliverableType.EMAIL


def test_monitor_recommendation_has_nothing_to_do() -> None:
    with pytest.raises(ValidationError):
        expected_type(Intent.FROM_RECOMMENDATION, {"id": "rec_1", "next_action": None})


def test_outreach_and_chat() -> None:
    influencer = {"id": "inf_1"}
    assert expected_type(Intent.INFLUENCER_OUTREACH, influencer) is (
        DeliverableType.INFLUENCER_OUTREACH
    )
    assert expected_type(Intent.CHAT, None) is None
