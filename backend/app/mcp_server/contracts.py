"""Typed MCP boundary contracts and raw-argument parsing."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import Field, ValidationError, model_serializer

from app.core.errors import NotFoundError
from app.core.errors import ValidationError as DomainValidationError
from app.intelligence.models import (
    ActivitySummary,
    ActivityType,
    Channel,
    Company,
    Competitor,
    CompetitorActivity,
    Influencer,
    ModelBase,
    Recommendation,
    Trend,
    TrendDirection,
)

ResultT = TypeVar("ResultT", bound=ModelBase)
ArgumentsT = TypeVar("ArgumentsT", bound=ModelBase)
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_TOOL_LIMIT = 10
MAX_TOOL_LIMIT = 25
NO_RECORDS_MATCHED_NOTE = "No records matched the request."


class ToolError(ModelBase):
    code: str
    message: str


class ToolErrorEnvelope(ModelBase):
    error: ToolError


class ResultsResponse(ModelBase, Generic[ResultT]):
    results: list[ResultT]
    note: str | None = None

    @model_serializer
    def serialize(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "results": [result.model_dump(mode="json") for result in self.results]
        }
        if self.note is not None:
            payload["note"] = self.note
        return payload


class RecordResponse(ModelBase, Generic[ResultT]):
    """Render a typed record as MCP text JSON using public, not Mongo, field names."""

    record: ResultT

    @model_serializer
    def serialize(self) -> dict[str, object]:
        return self.record.model_dump(mode="json")


class ActivitySearchArguments(ModelBase):
    query: str | None = None
    competitor_ids: list[str] | None = None
    activity_types: list[ActivityType] | None = None
    channels: list[Channel] | None = None
    since_days: int = Field(default=DEFAULT_LOOKBACK_DAYS, ge=1)
    limit: int = Field(default=DEFAULT_TOOL_LIMIT, ge=1)


class ActivitySummaryArguments(ModelBase):
    since_days: int = Field(default=DEFAULT_LOOKBACK_DAYS, ge=1)


class TrendSearchArguments(ModelBase):
    query: str | None = None
    channels: list[Channel] | None = None
    direction: TrendDirection | None = None
    limit: int = Field(default=DEFAULT_TOOL_LIMIT, ge=1)


class InfluencerSearchArguments(ModelBase):
    topic: str | None = None
    channels: list[Channel] | None = None
    region: str | None = None
    min_followers: int | None = Field(default=None, ge=0)
    limit: int = Field(default=DEFAULT_TOOL_LIMIT, ge=1)


class ActivityIdArguments(ModelBase):
    activity_id: str = Field(min_length=1)


class InfluencerIdArguments(ModelBase):
    influencer_id: str = Field(min_length=1)


class RecommendationIdArguments(ModelBase):
    recommendation_id: str = Field(min_length=1)


def parse_tool_arguments(
    argument_model: type[ArgumentsT], raw_arguments: dict[str, object]
) -> ArgumentsT | ToolErrorEnvelope:
    """Parse raw JSON tool input into one typed model or a recoverable envelope."""

    try:
        values = {name: value for name, value in raw_arguments.items() if value is not None}
        return argument_model.model_validate(values)
    except ValidationError as exc:
        return ToolErrorEnvelope(
            error=ToolError(
                code=DomainValidationError.code,
                message=_validation_message(exc),
            )
        )


def not_found(message: str) -> ToolErrorEnvelope:
    """Build the documented missing-record envelope."""

    return ToolErrorEnvelope(error=ToolError(code=NotFoundError.code, message=message))


def record_response(record: ResultT) -> RecordResponse[ResultT]:
    """Keep typed records inside the boundary while serializing public field names."""

    return RecordResponse[ResultT](record=record)


def capped_limit(limit: int) -> int:
    """Apply the one documented upper bound after typed lower-bound validation."""

    return min(limit, MAX_TOOL_LIMIT)


def _validation_message(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
        for detail in error.errors()
    )


CompanyResult = RecordResponse[Company] | ToolErrorEnvelope
CompetitorResults = ResultsResponse[Competitor] | ToolErrorEnvelope
ActivityResults = ResultsResponse[CompetitorActivity] | ToolErrorEnvelope
ActivityResult = RecordResponse[CompetitorActivity] | ToolErrorEnvelope
ActivitySummaryResult = RecordResponse[ActivitySummary] | ToolErrorEnvelope
TrendResults = ResultsResponse[Trend] | ToolErrorEnvelope
InfluencerResults = ResultsResponse[Influencer] | ToolErrorEnvelope
InfluencerResult = RecordResponse[Influencer] | ToolErrorEnvelope
RecommendationResult = RecordResponse[Recommendation] | ToolErrorEnvelope
