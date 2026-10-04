"""Proposed actions: payloads built in code from the deliverable (agents-spec §8, design D3)."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.agents.execution.output import ActionProposal
from app.connectors.payloads import validate_payload
from app.intelligence.models import (
    ActionType,
    Channel,
    Deliverable,
    DeliverableType,
    ProposedAction,
    ProposedActionStatus,
)

SCHEDULE_ZONE = ZoneInfo("Australia/Sydney")
SCHEDULE_TIME = time(9)
MAX_SLUG_CHARS = 80
SATURDAY = 5

# Where a post goes when the deliverable names no channel.
DEFAULT_CHANNELS: dict[DeliverableType, Channel] = {
    DeliverableType.LINKEDIN_POST: Channel.LINKEDIN,
    DeliverableType.X_POST: Channel.X,
    DeliverableType.INSTAGRAM_POST: Channel.INSTAGRAM,
    DeliverableType.CEO_POST: Channel.LINKEDIN,
    DeliverableType.BLOG_DRAFT: Channel.WEBSITE,
    DeliverableType.BLOG_OUTLINE: Channel.WEBSITE,
}


def next_weekday_morning(now: datetime) -> datetime:
    """The default schedule: the next weekday at 09:00 in Australia/Sydney."""
    day = now.astimezone(SCHEDULE_ZONE).date() + timedelta(days=1)
    while day.weekday() >= SATURDAY:
        day += timedelta(days=1)
    return datetime.combine(day, SCHEDULE_TIME, SCHEDULE_ZONE)


def schedule(when: str | None, now: datetime) -> datetime:
    """The user's time if the agent passed one on, read in Sydney when it has no zone."""
    if when:
        try:
            return datetime.combine(date.fromisoformat(when), SCHEDULE_TIME, SCHEDULE_ZONE)
        except ValueError:
            pass
        try:
            parsed = datetime.fromisoformat(when)
        except ValueError:
            # ponytail: an unreadable time falls back to the default; the user can still
            # change scheduled_for when approving.
            return next_weekday_morning(now)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=SCHEDULE_ZONE)
    return next_weekday_morning(now)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:MAX_SLUG_CHARS].rstrip("-") or "draft"


@dataclass(frozen=True)
class ActionSource:
    """What a payload is built from: never from model-written payload fields."""

    deliverable: Deliverable
    trigger: Mapping[str, object] | None
    when: str | None
    now: datetime

    def channel(self) -> Channel | None:
        return self.deliverable.channel or DEFAULT_CHANNELS.get(self.deliverable.type)

    def trigger_of(self, prefix: str) -> Mapping[str, object] | None:
        if self.trigger is not None and str(self.trigger.get("id", "")).startswith(prefix):
            return self.trigger
        return None


def social_post(src: ActionSource) -> dict[str, object]:
    return {
        "channel": src.channel(),
        "scheduled_for": schedule(src.when, src.now).isoformat(),
        "text": src.deliverable.body_markdown,
        "deliverable_id": src.deliverable.id,
    }


def cms_draft(src: ActionSource) -> dict[str, object]:
    return {
        "title": src.deliverable.title,
        "body_markdown": src.deliverable.body_markdown,
        "slug": slugify(src.deliverable.title),
        "tags": [],
    }


def email_draft(src: ActionSource) -> dict[str, object]:
    influencer = src.trigger_of("inf_") or {}
    return {
        "to_name": influencer.get("name"),
        "to_handle_or_email": influencer.get("handle"),
        "subject": src.deliverable.title,
        "body": src.deliverable.body_markdown,
    }


def calendar_entry(src: ActionSource) -> dict[str, object]:
    recommendation = src.trigger_of("rec_") or {}
    return {
        "title": src.deliverable.title,
        "channel": src.channel(),
        "date": schedule(src.when, src.now).date().isoformat(),
        "recommendation_id": recommendation.get("id"),
    }


PAYLOAD_BUILDERS: dict[ActionType, Callable[[ActionSource], dict[str, object]]] = {
    ActionType.SCHEDULE_SOCIAL_POST: social_post,
    ActionType.CREATE_CMS_DRAFT: cms_draft,
    ActionType.CREATE_EMAIL_DRAFT: email_draft,
    ActionType.ADD_TO_CONTENT_CALENDAR: calendar_entry,
}


def build_actions(
    deliverable: Deliverable,
    proposals: list[ActionProposal],
    trigger: Mapping[str, object] | None,
    now: datetime | None = None,
) -> list[ProposedAction]:
    """PROPOSED actions with validated payloads; nothing runs until a person approves."""
    now = now or datetime.now(UTC)
    actions = []
    for proposal in proposals:
        source = ActionSource(deliverable, trigger, proposal.when, now)
        payload = validate_payload(
            proposal.action_type, PAYLOAD_BUILDERS[proposal.action_type](source)
        )
        actions.append(
            ProposedAction(
                id=ProposedAction.new_id(),
                deliverable_id=deliverable.id,
                action_type=proposal.action_type,
                summary=proposal.summary,
                payload=payload,
                status=ProposedActionStatus.PROPOSED,
                created_at=now,
                updated_at=now,
            )
        )
    return actions
