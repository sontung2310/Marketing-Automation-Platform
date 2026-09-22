"""Load and validate the deterministic Step 1 demo seed."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, TypeAdapter

from app.intelligence.models import (
    ActivityType,
    Channel,
    Company,
    Competitor,
    CompetitorActivity,
    Influencer,
    SimulationTemplate,
    Trend,
    ensure_aware,
)

SEED_DIRECTORY = Path(__file__).resolve().parent
SEED_AUTHORED_AT = datetime(2026, 9, 22, tzinfo=UTC)
TModel = TypeVar("TModel", bound=BaseModel)


class SeedValidationError(ValueError):
    """Raised when seed data violates a documented coverage rule."""


class SeedBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    companies: list[Company]
    competitors: list[Competitor]
    competitor_activities: list[CompetitorActivity]
    trends: list[Trend]
    influencers: list[Influencer]
    simulation_templates: list[SimulationTemplate]


@dataclass(frozen=True)
class SeedCoverage:
    counts: dict[str, int]
    activity_types: dict[str, int]
    activity_channels: tuple[str, ...]
    trend_channels: tuple[str, ...]
    trend_directions: tuple[str, ...]
    influencer_channels: tuple[str, ...]
    au_influencer_ratio: float


def load_seed_bundle(
    directory: Path = SEED_DIRECTORY, *, now: datetime | None = None
) -> SeedBundle:
    """Load typed seed data and rebase its authored timestamps to load time."""

    bundle = SeedBundle(
        companies=_load(directory / "companies.json", list[Company]),
        competitors=_load(directory / "competitors.json", list[Competitor]),
        competitor_activities=_load(
            directory / "competitor_activities.json", list[CompetitorActivity]
        ),
        trends=_load(directory / "trends.json", list[Trend]),
        influencers=_load(directory / "influencers.json", list[Influencer]),
        simulation_templates=_load(
            directory / "simulation_templates.json", list[SimulationTemplate]
        ),
    )
    return _rebase_datetimes(bundle, now=ensure_aware(now or datetime.now(UTC)))


def validate_seed_bundle(bundle: SeedBundle, *, now: datetime | None = None) -> SeedCoverage:
    """Enforce the minimum demo coverage from data-contract.md §5."""

    if len(bundle.companies) < 1:
        raise SeedValidationError("seed requires at least one company")
    company = next((item for item in bundle.companies if item.id == "cmp_marketing_eye"), None)
    if company is None or len(company.icp) < 2 or len(company.services) < 5:
        raise SeedValidationError("Marketing Eye requires two ICP segments and five services")
    if len(company.content_pillars) < 4:
        raise SeedValidationError("Marketing Eye requires four content pillars")

    competitor_names = {item.name for item in bundle.competitors}
    if "Lyfe Marketing" not in competitor_names:
        raise SeedValidationError("seed requires Lyfe Marketing")
    fictional = [item for item in bundle.competitors if item.is_fictional]
    if not {item.name for item in fictional}.issuperset(
        {"Brightlane Marketing", "Kestrel Growth Co."}
    ):
        raise SeedValidationError("seed requires Brightlane Marketing and Kestrel Growth Co.")
    if any(not item.executives for item in fictional):
        raise SeedValidationError("every fictional competitor needs a named executive")

    if len(bundle.competitor_activities) < 45:
        raise SeedValidationError("seed requires at least 45 competitor activities")
    activity_counts = Counter(item.activity_type.value for item in bundle.competitor_activities)
    missing_types = [item.value for item in ActivityType if activity_counts[item.value] < 3]
    if missing_types:
        raise SeedValidationError(f"activity coverage is missing: {', '.join(missing_types)}")
    required_activity_channels = {Channel.WEBSITE, Channel.LINKEDIN, Channel.X, Channel.INSTAGRAM}
    activity_channels = {item.channel for item in bundle.competitor_activities}
    if not required_activity_channels.issubset(activity_channels):
        missing = sorted(item.value for item in required_activity_channels - activity_channels)
        raise SeedValidationError(f"activity channel coverage is missing: {', '.join(missing)}")
    detected = [item.detected_at for item in bundle.competitor_activities]
    current_time = ensure_aware(now or datetime.now(UTC))
    if any(item > current_time for item in detected):
        raise SeedValidationError("activities cannot be dated in the future")
    if any(item < current_time - timedelta(days=30) for item in detected):
        raise SeedValidationError("activities must fall within the last 30 days")
    if sum(item >= current_time - timedelta(hours=48) for item in detected) < 6:
        raise SeedValidationError("at least six activities must fall within the latest 48 hours")

    if any(not _is_mock(item) for item in _all_records(bundle)):
        raise SeedValidationError("every seeded record must set is_mock=true")
    fictional_ids = {item.id for item in fictional}
    real_ids = {item.id for item in bundle.competitors if not item.is_fictional}
    if any(
        item.competitor_id in real_ids and item.is_mock and not item.is_simulated
        for item in bundle.competitor_activities
    ):
        raise SeedValidationError("real competitors cannot have fabricated mock activities")
    restricted_types = {
        ActivityType.SOCIAL_POST,
        ActivityType.EXECUTIVE_POST,
        ActivityType.PROMOTION,
        ActivityType.CAMPAIGN_LAUNCH,
    }
    if any(
        item.activity_type in restricted_types and item.competitor_id not in fictional_ids
        for item in bundle.competitor_activities
    ):
        raise SeedValidationError(
            "social, executive, promotion and campaign mocks must be fictional"
        )
    if any(item.is_fictional and not _uses_example_hostname(item.website) for item in fictional):
        raise SeedValidationError("fictional competitor websites must use .example")
    if any(
        url is not None and not _uses_example_hostname(url)
        for item in fictional
        for url in item.social.values()
    ):
        raise SeedValidationError("fictional competitor social URLs must use .example")
    if any(
        item.competitor_id in fictional_ids
        and item.url is not None
        and not _uses_example_hostname(item.url)
        for item in bundle.competitor_activities
    ):
        raise SeedValidationError("fictional competitor activity URLs must use .example")
    if any(
        not _uses_example_hostname(sample_post.url)
        for trend in bundle.trends
        for sample_post in trend.sample_posts
    ):
        raise SeedValidationError("trend sample post URLs must use .example")
    competitors_by_id = {item.id: item for item in bundle.competitors}
    for template in bundle.simulation_templates:
        template_competitor = competitors_by_id.get(template.competitor_id)
        if template_competitor is None or not template_competitor.is_fictional:
            raise SeedValidationError(
                "simulation templates must target fictional seeded competitors"
            )
        if not template.url or not _uses_example_hostname(template.url):
            raise SeedValidationError("simulation template URLs must use .example")

    if len(bundle.trends) < 16:
        raise SeedValidationError("seed requires at least 16 trends")
    required_trend_channels = {Channel.LINKEDIN, Channel.X, Channel.REDDIT, Channel.NEWS}
    trend_channels = {item.channel for item in bundle.trends}
    if not required_trend_channels.issubset(trend_channels):
        raise SeedValidationError("trend channels must cover LinkedIn, X, Reddit and News")
    trend_directions = {item.direction.value for item in bundle.trends}
    if trend_directions != {"RISING", "STEADY", "FALLING"}:
        raise SeedValidationError("trends must include rising, steady and falling directions")
    activity_topics = {
        topic.lower() for item in bundle.competitor_activities for topic in item.topics
    }
    overlaps = sum(
        bool(activity_topics & {keyword.lower() for keyword in item.keywords})
        for item in bundle.trends
    )
    if overlaps < 4:
        raise SeedValidationError("at least four trends must overlap activity topics")

    if len(bundle.influencers) < 20:
        raise SeedValidationError("seed requires at least 20 influencers")
    required_influencer_channels = {Channel.LINKEDIN, Channel.X, Channel.YOUTUBE}
    influencer_channels = {item.channel for item in bundle.influencers}
    if not required_influencer_channels.issubset(influencer_channels):
        raise SeedValidationError("influencer channels must cover LinkedIn, X and YouTube")
    au_ratio = sum(item.audience_region == "AU" for item in bundle.influencers) / len(
        bundle.influencers
    )
    if au_ratio < 0.6:
        raise SeedValidationError("at least 60% of influencers must have AU audiences")
    scores = [item.relevance_score for item in bundle.influencers]
    if min(scores) > 0.3 or max(scores) < 0.95:
        raise SeedValidationError("influencer relevance scores must span 0.3 to 0.95")

    template_counts = Counter(item.activity_type.value for item in bundle.simulation_templates)
    missing_templates = [item.value for item in ActivityType if template_counts[item.value] < 2]
    if missing_templates:
        raise SeedValidationError(
            f"simulation templates are missing: {', '.join(missing_templates)}"
        )
    return SeedCoverage(
        counts={
            "companies": len(bundle.companies),
            "competitors": len(bundle.competitors),
            "competitor_activities": len(bundle.competitor_activities),
            "trends": len(bundle.trends),
            "influencers": len(bundle.influencers),
            "simulation_templates": len(bundle.simulation_templates),
        },
        activity_types=dict(sorted(activity_counts.items())),
        activity_channels=tuple(sorted(item.value for item in activity_channels)),
        trend_channels=tuple(sorted(item.value for item in trend_channels)),
        trend_directions=tuple(sorted(trend_directions)),
        influencer_channels=tuple(sorted(item.value for item in influencer_channels)),
        au_influencer_ratio=au_ratio,
    )


def _load(path: Path, target: type[list[TModel]]) -> list[TModel]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedValidationError(f"could not read {path.name}: {exc}") from exc
    return TypeAdapter(target).validate_python(payload)


def _rebase_datetimes(bundle: SeedBundle, *, now: datetime) -> SeedBundle:
    """Shift every datetime in the typed bundle by its load-time offset."""

    return _shift_datetime_values(bundle, offset=now - SEED_AUTHORED_AT)


def _shift_datetime_values(model: TModel, *, offset: timedelta) -> TModel:
    """Recursively shift datetime fields while preserving Pydantic model types."""

    return model.model_copy(
        update={
            field_name: _shift_datetime_value(value, offset=offset) for field_name, value in model
        }
    )


def _shift_datetime_value(value: object, *, offset: timedelta) -> object:
    if isinstance(value, datetime):
        return value + offset
    if isinstance(value, BaseModel):
        return _shift_datetime_values(value, offset=offset)
    if isinstance(value, list):
        return [_shift_datetime_value(item, offset=offset) for item in value]
    if isinstance(value, dict):
        return {key: _shift_datetime_value(item, offset=offset) for key, item in value.items()}
    return value


def _uses_example_hostname(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return (
        parsed.username is None
        and (hostname := parsed.hostname) is not None
        and hostname.endswith(".example")
    )


def _all_records(bundle: SeedBundle) -> list[BaseModel]:
    return [
        *bundle.companies,
        *bundle.competitors,
        *bundle.competitor_activities,
        *bundle.trends,
        *bundle.influencers,
        *bundle.simulation_templates,
    ]


def _is_mock(record: BaseModel) -> bool:
    return getattr(record, "is_mock", False) is True
