"""Proposed actions: payloads built in code from the deliverable (agents-spec §8, design D3)."""

import asyncio
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pydantic

from app.agents.execution.output import ActionProposal
from app.agents.execution.validation import CHANNEL_FOR
from app.connectors.base import Connector
from app.connectors.payloads import validate_payload
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.intelligence.models import (
    ActionType,
    Channel,
    Deliverable,
    DeliverableType,
    Influencer,
    ProposedAction,
    ProposedActionStatus,
    Recommendation,
)
from app.intelligence.repositories import ProposedActionsRepository

logger = logging.getLogger(__name__)

SCHEDULE_ZONE = ZoneInfo("Australia/Sydney")
SCHEDULE_TIME = time(9)
MAX_SLUG_CHARS = 80
PINNED_FIELDS = ("deliverable_id",)
SATURDAY = 5

# Where a post goes when the deliverable names no channel.
DEFAULT_CHANNELS: dict[DeliverableType, Channel] = CHANNEL_FOR | {
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


def parse_when(when: str) -> datetime | None:
    """A date or time the user named, read in Sydney when it has no zone."""
    try:
        return datetime.combine(date.fromisoformat(when), SCHEDULE_TIME, SCHEDULE_ZONE)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(when)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=SCHEDULE_ZONE)


def schedule(when: str | None, now: datetime) -> datetime:
    """The user's time if the agent passed one on; otherwise, or when it is unreadable or
    already past, the default. The user can still change it when approving."""
    parsed = parse_when(when) if when else None
    if when and parsed is None:
        logger.warning("Unreadable schedule %r; using the default", when)
    return parsed if parsed is not None and parsed > now else next_weekday_morning(now)


def is_past(payload: Mapping[str, object], now: datetime) -> bool:
    """Whether a validated payload's schedule (a time or a Sydney date) has already gone."""
    if isinstance(at := payload.get("scheduled_for"), str):
        return datetime.fromisoformat(at) <= now
    if isinstance(day := payload.get("date"), str):
        return date.fromisoformat(day) < now.astimezone(SCHEDULE_ZONE).date()
    return False


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
    influencer = src.trigger_of(Influencer.id_prefix) or {}
    return {
        "to_name": influencer.get("name"),
        "to_handle_or_email": influencer.get("handle"),
        "subject": src.deliverable.title,
        "body": src.deliverable.body_markdown,
    }


def calendar_entry(src: ActionSource) -> dict[str, object]:
    recommendation = src.trigger_of(Recommendation.id_prefix) or {}
    return {
        "title": src.deliverable.title,
        "channel": src.channel(),
        "date": schedule(src.when, src.now).astimezone(SCHEDULE_ZONE).date().isoformat(),
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
    *,
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


class ActionService:
    """Approve or discard a PROPOSED action (agents-spec §8 state machine).

    ponytail: no tenant or ownership check; one tenant and no auth in the PoC. Add a
    company_id to ProposedAction and check it here when auth lands.
    """

    def __init__(
        self,
        actions: ProposedActionsRepository,
        connectors: Mapping[ActionType, Connector],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.actions = actions
        self.connectors = connectors
        self.clock = clock

    async def approve(
        self, action_id: str, overrides: Mapping[str, object] | None = None
    ) -> ProposedAction:
        action = await self._proposed(action_id)
        try:
            # Overrides edit the content, never which deliverable the action belongs to.
            pinned = {k: action.payload[k] for k in PINNED_FIELDS if k in action.payload}
            payload = validate_payload(
                action.action_type, action.payload | dict(overrides or {}) | pinned
            )
        except pydantic.ValidationError as exc:
            raise ValidationError(
                "The action payload is not valid", {"errors": exc.errors(include_url=False)}
            ) from exc
        if is_past(payload, self.clock()):
            raise ValidationError("The schedule is in the past; choose a later time", {})
        approved = await self.actions.transition(
            action_id,
            ProposedActionStatus.PROPOSED,
            {
                "status": ProposedActionStatus.APPROVED,
                "payload": payload,
                "updated_at": self.clock(),
            },
        )
        if approved is None:
            raise self._conflict(action_id)  # another request approved or discarded it first
        # ponytail: a process that dies mid-run still leaves the action APPROVED; a sweeper
        # that fails stale APPROVED actions fixes that when real connectors land.
        try:
            receipt = await self.connectors[action.action_type].execute(payload)
        except BaseException as exc:  # a cancelled request must not strand it as APPROVED
            logger.exception("Connector failed for %s", action_id)
            failed: dict[str, object] = {
                "status": ProposedActionStatus.FAILED,
                "error": f"The {action.action_type} connector failed. The error has been logged.",
            }
            done = await asyncio.shield(self._settle(action_id, failed))
            if not isinstance(exc, Exception):
                raise
            return done
        return await self._settle(
            action_id, {"status": ProposedActionStatus.EXECUTED, "receipt": receipt}
        )

    async def _settle(self, action_id: str, outcome: dict[str, object]) -> ProposedAction:
        done = await self.actions.transition(
            action_id, ProposedActionStatus.APPROVED, outcome | {"updated_at": self.clock()}
        )
        if done is None:
            raise ConflictError(f"{action_id} changed while it ran", {"action_id": action_id})
        return done

    async def discard(self, action_id: str) -> ProposedAction:
        await self._proposed(action_id)
        discarded = await self.actions.transition(
            action_id,
            ProposedActionStatus.PROPOSED,
            {"status": ProposedActionStatus.DISCARDED, "updated_at": self.clock()},
        )
        if discarded is None:
            raise self._conflict(action_id)
        return discarded

    async def _proposed(self, action_id: str) -> ProposedAction:
        action = await self.actions.get(action_id)
        if action is None:
            raise NotFoundError(f"{action_id} was not found", {"action_id": action_id})
        if action.status is not ProposedActionStatus.PROPOSED:
            raise self._conflict(action_id, action.status)
        return action

    @staticmethod
    def _conflict(action_id: str, status: object = None) -> ConflictError:
        detail = f" (it is {status})" if status else ""
        return ConflictError(
            f"{action_id} is no longer awaiting approval{detail}", {"action_id": action_id}
        )
