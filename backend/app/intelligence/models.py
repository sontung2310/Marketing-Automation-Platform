"""Typed contracts for the platform-owned MongoDB collections."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ulid import ULID


class ActivityType(StrEnum):
    NEW_BLOG = "NEW_BLOG"
    SOCIAL_POST = "SOCIAL_POST"
    EXECUTIVE_POST = "EXECUTIVE_POST"
    NEW_PRODUCT = "NEW_PRODUCT"
    PRODUCT_REMOVED = "PRODUCT_REMOVED"
    PRICE_CHANGE = "PRICE_CHANGE"
    PROMOTION = "PROMOTION"
    CAMPAIGN_LAUNCH = "CAMPAIGN_LAUNCH"
    PAGE_UPDATE = "PAGE_UPDATE"


class Channel(StrEnum):
    WEBSITE = "WEBSITE"
    LINKEDIN = "LINKEDIN"
    X = "X"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    YOUTUBE = "YOUTUBE"
    REDDIT = "REDDIT"
    NEWS = "NEWS"


class SourceSystem(StrEnum):
    COMPETITORSCOPE = "COMPETITORSCOPE"
    DCT = "DCT"
    PACE = "PACE"
    MOCK_SEED = "MOCK_SEED"
    SIMULATED = "SIMULATED"


class TrendDirection(StrEnum):
    RISING = "RISING"
    STEADY = "STEADY"
    FALLING = "FALLING"


class Priority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AgentName(StrEnum):
    STRATEGY = "STRATEGY"
    EXECUTION = "EXECUTION"


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REFUSED = "REFUSED"


class RecommendationStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    SUPERSEDED = "SUPERSEDED"  # a later Strategy run in the same session replaced it


class ProposedActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    EXECUTED = "EXECUTED"
    DISCARDED = "DISCARDED"
    FAILED = "FAILED"


class DeliverableType(StrEnum):
    BLOG_DRAFT = "BLOG_DRAFT"
    BLOG_OUTLINE = "BLOG_OUTLINE"
    LINKEDIN_POST = "LINKEDIN_POST"
    X_POST = "X_POST"
    INSTAGRAM_POST = "INSTAGRAM_POST"
    CEO_POST = "CEO_POST"
    EMAIL = "EMAIL"
    AD_COPY = "AD_COPY"
    RESPONSE_BRIEF = "RESPONSE_BRIEF"
    INFLUENCER_OUTREACH = "INFLUENCER_OUTREACH"


class ActionType(StrEnum):
    SCHEDULE_SOCIAL_POST = "schedule_social_post"
    CREATE_CMS_DRAFT = "create_cms_draft"
    CREATE_EMAIL_DRAFT = "create_email_draft"
    ADD_TO_CONTENT_CALENDAR = "add_to_content_calendar"


class ModelBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=False)


class PrefixedModel(ModelBase):
    id: str = Field(alias="_id")
    id_prefix: ClassVar[str] = ""

    @field_validator("id")
    @classmethod
    def validate_id_prefix(cls, value: str) -> str:
        if not value.startswith(cls.id_prefix) or len(value) == len(cls.id_prefix):
            raise ValueError(f"id must start with {cls.id_prefix!r}")
        return value

    @classmethod
    def new_id(cls) -> str:
        return f"{cls.id_prefix}{ULID()}"


class TenantModel(PrefixedModel):
    company_id: str

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, value: str) -> str:
        if not value.startswith("cmp_"):
            raise ValueError("company_id must start with 'cmp_'")
        return value


class Provenance(ModelBase):
    system: SourceSystem
    ref_id: str = Field(min_length=1)


class ICP(ModelBase):
    segment: str = Field(min_length=1)
    pains: list[str] = Field(min_length=1)
    goals: list[str] = Field(min_length=1)


class Service(ModelBase):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    price_from: float = Field(ge=0)


class BrandVoice(ModelBase):
    tone: list[str] = Field(min_length=1)
    do: list[str] = Field(min_length=1)
    dont: list[str] = Field(min_length=1)
    sample_copy: list[str] = Field(min_length=1)


class Company(PrefixedModel):
    id_prefix: ClassVar[str] = "cmp_"
    name: str = Field(min_length=1)
    website: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    region: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    icp: list[ICP] = Field(min_length=1)
    positioning: str = Field(min_length=1)
    services: list[Service] = Field(min_length=1)
    brand_voice: BrandVoice
    channels: list[Channel] = Field(min_length=1)
    content_pillars: list[str] = Field(min_length=1)
    is_mock: bool
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def updated_at_is_aware(cls, value: datetime) -> datetime:
        return ensure_aware(value)


class Executive(ModelBase):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)


class Competitor(TenantModel):
    id_prefix: ClassVar[str] = "cpt_"
    name: str = Field(min_length=1)
    website: str = Field(min_length=1)
    is_fictional: bool
    social: dict[Channel, str | None] = Field(default_factory=dict)
    executives: list[Executive] = Field(default_factory=list)
    source: Provenance
    is_mock: bool

    @model_validator(mode="after")
    def fictional_executive_rule(self) -> Competitor:
        if not self.is_fictional and self.executives:
            raise ValueError("non-fictional competitors cannot have fictional executives")
        return self


class Price(ModelBase):
    before: float = Field(ge=0)
    after: float = Field(ge=0)
    currency: str = Field(min_length=1, max_length=3)


class Engagement(ModelBase):
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)


class ActivityAuthor(ModelBase):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)


class CompetitorActivity(TenantModel):
    id_prefix: ClassVar[str] = "act_"
    competitor_id: str
    competitor_name: str = Field(min_length=1)
    activity_type: ActivityType
    channel: Channel
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    narrative_summary: str | None = None
    url: str | None = None
    author: ActivityAuthor | None = None
    price: Price | None = None
    engagement: Engagement | None = None
    content_excerpt: str | None = Field(default=None, max_length=1200)
    topics: list[str] = Field(default_factory=list)
    occurred_at: datetime
    detected_at: datetime
    source: Provenance
    is_mock: bool
    is_simulated: bool
    seen_at: datetime | None = None
    ingested_at: datetime

    @field_validator("competitor_id")
    @classmethod
    def validate_competitor_id(cls, value: str) -> str:
        if not value.startswith("cpt_"):
            raise ValueError("competitor_id must start with 'cpt_'")
        return value

    @field_validator("occurred_at", "detected_at", "seen_at", "ingested_at")
    @classmethod
    def timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        return ensure_aware(value) if value is not None else None

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> CompetitorActivity:
        social_types = {ActivityType.SOCIAL_POST, ActivityType.EXECUTIVE_POST}
        if self.activity_type != ActivityType.EXECUTIVE_POST and self.author is not None:
            raise ValueError("author is only valid for EXECUTIVE_POST")
        price_types = {ActivityType.PRICE_CHANGE, ActivityType.PROMOTION}
        if self.activity_type not in price_types and self.price is not None:
            raise ValueError("price is only valid for PRICE_CHANGE or PROMOTION")
        if self.activity_type not in social_types and self.engagement is not None:
            raise ValueError("engagement is only valid for social activity types")
        return self


class ActivitySummaryCount(ModelBase):
    competitor_id: str
    competitor_name: str
    activity_type: ActivityType
    count: int = Field(ge=0)


class ActivitySummaryRecent(ModelBase):
    competitor_id: str
    competitor_name: str
    items: list[CompetitorActivity] = Field(default_factory=list)


class ActivitySummary(ModelBase):
    counts: list[ActivitySummaryCount] = Field(default_factory=list)
    recent_items: list[ActivitySummaryRecent] = Field(default_factory=list)
    note: str | None = None


class SamplePost(ModelBase):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    channel: Channel


class Trend(TenantModel):
    id_prefix: ClassVar[str] = "trd_"
    topic: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    channel: Channel
    window_days: int = Field(gt=0)
    mention_count: int = Field(ge=0)
    momentum_pct: float
    direction: TrendDirection
    sentiment: float = Field(ge=-1, le=1)
    sample_posts: list[SamplePost] = Field(min_length=1)
    computed_at: datetime
    source: Provenance
    is_mock: bool

    @field_validator("computed_at")
    @classmethod
    def computed_at_is_aware(cls, value: datetime) -> datetime:
        return ensure_aware(value)


class EvidenceLink(ModelBase):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)


class Influencer(TenantModel):
    id_prefix: ClassVar[str] = "inf_"
    name: str = Field(min_length=1)
    handle: str = Field(min_length=1)
    channel: Channel
    profile_url: str = Field(min_length=1)
    followers: int = Field(ge=0)
    engagement_rate: float = Field(ge=0, le=1)
    topics: list[str] = Field(default_factory=list)
    audience_region: str = Field(min_length=1)
    relevance_score: float = Field(ge=0, le=1)
    evidence: list[EvidenceLink] = Field(default_factory=list)
    source: Provenance
    is_mock: bool


class Session(TenantModel):
    id_prefix: ClassVar[str] = "ses_"
    created_at: datetime
    last_run_id: str | None = None

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        return ensure_aware(value)

    @field_validator("last_run_id")
    @classmethod
    def validate_last_run_id(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("run_"):
            raise ValueError("last_run_id must start with 'run_'")
        return value


class Run(PrefixedModel):
    id_prefix: ClassVar[str] = "run_"
    session_id: str
    agent: AgentName
    intent: str = Field(min_length=1)
    trigger: dict[str, object] = Field(default_factory=dict)
    route: dict[str, object] = Field(default_factory=dict)
    status: RunStatus
    events: list[dict[str, object]] = Field(default_factory=list)
    tool_calls: list[dict[str, object]] = Field(default_factory=list)
    skills_loaded: list[str] = Field(default_factory=list)
    output: dict[str, object] | None = None
    usage: dict[str, object] | None = None
    error: dict[str, object] | None = None
    started_at: datetime
    finished_at: datetime | None = None

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not value.startswith("ses_"):
            raise ValueError("session_id must start with 'ses_'")
        return value

    @field_validator("started_at", "finished_at")
    @classmethod
    def run_timestamps_are_aware(cls, value: datetime | None) -> datetime | None:
        return ensure_aware(value) if value is not None else None


class NextAction(ModelBase):
    agent: Literal[AgentName.EXECUTION] = AgentName.EXECUTION
    deliverable_type: DeliverableType
    brief: str = Field(min_length=1)


class RecommendationEvidence(ModelBase):
    id: str = Field(min_length=1)
    kind: Literal["activity", "trend", "influencer", "company"]
    note: str = Field(min_length=1, max_length=140)


class Recommendation(PrefixedModel):
    id_prefix: ClassVar[str] = "rec_"
    run_id: str
    session_id: str
    ordinal: int = Field(gt=0)
    kind: Literal[
        "CONTENT_TOPIC",
        "COMPETITIVE_RESPONSE",
        "INFLUENCER_PARTNERSHIP",
        "CHANNEL_PLAY",
        "MONITOR",
    ]
    title: str = Field(min_length=1, max_length=90)
    rationale: str = Field(min_length=1)
    priority: Priority
    channel: Channel | None = None
    evidence: list[RecommendationEvidence] = Field(min_length=1)
    skills_used: list[str] = Field(default_factory=list)
    next_action: NextAction | None = None
    status: RecommendationStatus

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        if not value.startswith("run_"):
            raise ValueError("run_id must start with 'run_'")
        return value

    @field_validator("session_id")
    @classmethod
    def validate_recommendation_session_id(cls, value: str) -> str:
        if not value.startswith("ses_"):
            raise ValueError("session_id must start with 'ses_'")
        return value


class Deliverable(PrefixedModel):
    id_prefix: ClassVar[str] = "del_"
    run_id: str
    type: DeliverableType
    channel: Channel | None = None
    title: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)
    variants: list[str] = Field(default_factory=list, max_length=3)
    word_count: int = Field(ge=0)
    author_persona: str | None = None

    @field_validator("run_id")
    @classmethod
    def validate_deliverable_run_id(cls, value: str) -> str:
        if not value.startswith("run_"):
            raise ValueError("run_id must start with 'run_'")
        return value


class ProposedAction(PrefixedModel):
    id_prefix: ClassVar[str] = "pac_"
    deliverable_id: str
    action_type: ActionType
    summary: str = Field(min_length=1)
    payload: dict[str, object]
    status: ProposedActionStatus
    receipt: dict[str, object] | None = None
    proposed_at: datetime
    updated_at: datetime

    @field_validator("deliverable_id")
    @classmethod
    def validate_action_deliverable_id(cls, value: str) -> str:
        if not value.startswith("del_"):
            raise ValueError("deliverable_id must start with 'del_'")
        return value

    @field_validator("proposed_at", "updated_at")
    @classmethod
    def action_timestamps_are_aware(cls, value: datetime) -> datetime:
        return ensure_aware(value)


class SimulationTemplate(ModelBase):
    activity_type: ActivityType
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    channel: Channel
    competitor_id: str
    url: str | None = None
    content_excerpt: str | None = Field(default=None, max_length=1200)
    is_mock: bool

    @field_validator("competitor_id")
    @classmethod
    def validate_template_competitor_id(cls, value: str) -> str:
        if not value.startswith("cpt_"):
            raise ValueError("competitor_id must start with 'cpt_'")
        return value


def ensure_aware(value: datetime) -> datetime:
    """Require UTC-offset-aware timestamps at the persistence boundary."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return value


OwnedModel = (
    Company
    | Competitor
    | CompetitorActivity
    | Trend
    | Influencer
    | Session
    | Run
    | Recommendation
    | Deliverable
    | ProposedAction
)
