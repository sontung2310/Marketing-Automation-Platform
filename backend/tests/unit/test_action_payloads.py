"""Proposed-action payloads are built in code, with the Sydney weekday-morning default."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.agents.execution.output import ActionProposal
from app.connectors.payloads import PAYLOADS, validate_payload
from app.intelligence.models import ActionType, Channel, Deliverable, DeliverableType
from app.orchestration.actions import (
    PAYLOAD_BUILDERS,
    build_actions,
    next_weekday_morning,
    schedule,
    slugify,
)

# Friday 2026-10-09, 14:00 in Sydney (AEDT, UTC+11).
FRIDAY = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)


def item(deliverable_type: DeliverableType, channel: Channel | None = None) -> Deliverable:
    return Deliverable(
        id="del_1",
        run_id="run_1",
        type=deliverable_type,
        channel=channel,
        title="Positioning: a shared filter for decisions!",
        body_markdown="My view: positioning is a filter.",
        word_count=6,
    )


def propose(action_type: ActionType, when: str | None = None) -> ActionProposal:
    return ActionProposal(action_type=action_type, summary="Do it", when=when)


def test_friday_schedules_for_monday_nine_in_sydney() -> None:
    assert next_weekday_morning(FRIDAY).isoformat() == "2026-10-12T09:00:00+11:00"
    tuesday = datetime(2026, 10, 13, 0, 0, tzinfo=UTC)  # Tuesday 11:00 Sydney
    assert next_weekday_morning(tuesday).isoformat() == "2026-10-14T09:00:00+11:00"


def test_a_user_given_time_wins() -> None:
    assert schedule("2026-10-20T15:30:00+11:00", FRIDAY).isoformat() == (
        "2026-10-20T15:30:00+11:00"
    )
    assert schedule("2026-10-20T15:30:00", FRIDAY).isoformat() == "2026-10-20T15:30:00+11:00"
    assert schedule("2026-10-20", FRIDAY).isoformat() == "2026-10-20T09:00:00+11:00"
    assert schedule("next Tuesday", FRIDAY) == next_weekday_morning(FRIDAY)
    assert schedule("2020-01-01", FRIDAY) == next_weekday_morning(FRIDAY)  # already past


def test_a_calendar_entry_takes_the_sydney_date() -> None:
    late_utc = "2026-10-13T23:00:00+00:00"  # already Wednesday 10:00 in Sydney
    [entry] = build_actions(
        item(DeliverableType.LINKEDIN_POST),
        [propose(ActionType.ADD_TO_CONTENT_CALENDAR, late_utc)],
        trigger=None,
        now=FRIDAY,
    )
    assert entry.payload["date"] == "2026-10-14"


def test_every_action_type_has_a_builder_and_a_payload() -> None:
    assert set(PAYLOAD_BUILDERS) == set(PAYLOADS) == set(ActionType)


def test_invalid_payloads_are_rejected() -> None:
    with pytest.raises(ValidationError):  # no timezone
        validate_payload(
            ActionType.SCHEDULE_SOCIAL_POST,
            {
                "channel": "X",
                "scheduled_for": "2026-10-12T09:00:00",
                "text": "Hi",
                "deliverable_id": "del_1",
            },
        )
    with pytest.raises(ValidationError):  # unknown field
        validate_payload(
            ActionType.CREATE_EMAIL_DRAFT, {"subject": "S", "body": "B", "to_name": None, "cc": "x"}
        )


def test_social_post_payload_comes_from_the_deliverable() -> None:
    [action] = build_actions(
        item(DeliverableType.CEO_POST),
        [propose(ActionType.SCHEDULE_SOCIAL_POST)],
        trigger=None,
        now=FRIDAY,
    )
    assert action.status == "PROPOSED" and action.deliverable_id == "del_1"
    assert action.payload == {
        "channel": "LINKEDIN",  # a CEO post defaults to LinkedIn
        "scheduled_for": "2026-10-12T09:00:00+11:00",
        "text": "My view: positioning is a filter.",
        "deliverable_id": "del_1",
    }


def test_outreach_and_calendar_use_the_trigger_record() -> None:
    influencer = {"id": "inf_1", "name": "Priya Shah", "handle": "@priya"}
    [email] = build_actions(
        item(DeliverableType.INFLUENCER_OUTREACH),
        [propose(ActionType.CREATE_EMAIL_DRAFT)],
        trigger=influencer,
        now=FRIDAY,
    )
    assert (email.payload["to_name"], email.payload["to_handle_or_email"]) == (
        "Priya Shah",
        "@priya",
    )
    recommendation = {"id": "rec_1", "next_action": {}}
    [entry] = build_actions(
        item(DeliverableType.BLOG_DRAFT),
        [propose(ActionType.ADD_TO_CONTENT_CALENDAR, "2026-10-21")],
        trigger=recommendation,
        now=FRIDAY,
    )
    assert entry.payload == {
        "title": "Positioning: a shared filter for decisions!",
        "channel": "WEBSITE",
        "date": "2026-10-21",
        "owner": None,
        "recommendation_id": "rec_1",
    }


def test_cms_slug() -> None:
    assert slugify("Positioning: a shared filter for decisions!") == (
        "positioning-a-shared-filter-for-decisions"
    )
    assert slugify("!!!") == "draft"
