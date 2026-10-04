"""Typed payload for each action type (agents-spec §8), validated before a connector runs."""

from datetime import date

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.intelligence.models import ActionType, Channel


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SocialPostPayload(Payload):
    channel: Channel
    scheduled_for: AwareDatetime
    text: str = Field(min_length=1)
    deliverable_id: str = Field(pattern=r"^del_")


class CmsDraftPayload(Payload):
    title: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    tags: list[str]


class EmailDraftPayload(Payload):
    to_name: str | None  # None for an email with no named recipient (e.g. a newsletter)
    to_handle_or_email: str | None = None
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class CalendarEntryPayload(Payload):
    title: str = Field(min_length=1)
    channel: Channel | None
    date: date
    owner: str | None = None
    recommendation_id: str | None = None


PAYLOADS: dict[ActionType, type[Payload]] = {
    ActionType.SCHEDULE_SOCIAL_POST: SocialPostPayload,
    ActionType.CREATE_CMS_DRAFT: CmsDraftPayload,
    ActionType.CREATE_EMAIL_DRAFT: EmailDraftPayload,
    ActionType.ADD_TO_CONTENT_CALENDAR: CalendarEntryPayload,
}


def validate_payload(action_type: ActionType, payload: dict[str, object]) -> dict[str, object]:
    """The payload as stored JSON, or a pydantic ValidationError."""
    return PAYLOADS[action_type].model_validate(payload).model_dump(mode="json")
