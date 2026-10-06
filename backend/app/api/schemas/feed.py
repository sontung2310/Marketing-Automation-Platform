"""Request bodies and query parsing for the read-side routes (api-contract)."""

from datetime import datetime
from enum import StrEnum
from typing import TypeVar

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from app.core.errors import ValidationError
from app.intelligence.models import ActivityType, normalize_keywords

E = TypeVar("E", bound=StrEnum)


class TrackedKeywordsBody(BaseModel):
    tracked_keywords: list[str] = Field(min_length=1, max_length=20)

    @field_validator("tracked_keywords")
    @classmethod
    def normalized(cls, value: list[str]) -> list[str]:
        return normalize_keywords(value)


class MarkSeenBody(BaseModel):
    up_to: AwareDatetime


class SimulateBody(BaseModel):
    activity_type: ActivityType | None = None
    competitor_id: str | None = Field(default=None, max_length=64)


def parse_csv(raw: str | None, enum: type[E], name: str) -> list[E] | None:
    """The contract's CSV filters, validated against their enum."""
    if not raw:
        return None
    try:
        return [enum(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as error:
        raise ValidationError(f"{name} contains an unknown value", {"value": raw}) from error


def parse_ids(raw: str | None) -> list[str] | None:
    return [value.strip() for value in raw.split(",") if value.strip()] if raw else None


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValidationError("since must include a timezone")
    return value
