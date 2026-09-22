"""Create explicitly simulated competitor activities for the demo."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from random import Random
from uuid import uuid4

from pymongo.asynchronous.database import AsyncDatabase

from app.core.errors import ValidationError
from app.intelligence.models import (
    ActivityType,
    Competitor,
    CompetitorActivity,
    Provenance,
    SimulationTemplate,
    SourceSystem,
)
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.competitors import CompetitorsRepository

logger = logging.getLogger(__name__)
SIMULATION_REAL_COMPETITOR_ERROR = (
    "Simulated activity can only be created for fictional demo competitors"
)


def _template_matches(
    template: SimulationTemplate, *, competitor_id: str, activity_type: ActivityType | None
) -> bool:
    return template.competitor_id == competitor_id and (
        activity_type is None or template.activity_type == activity_type
    )


def _fictional_options(
    competitors: Sequence[Competitor],
    templates: Sequence[SimulationTemplate],
    activity_type: ActivityType | None,
) -> list[tuple[Competitor, list[SimulationTemplate]]]:
    return [
        (
            competitor,
            [
                template
                for template in templates
                if _template_matches(
                    template, competitor_id=competitor.id, activity_type=activity_type
                )
            ],
        )
        for competitor in competitors
        if competitor.is_fictional
        and any(
            _template_matches(template, competitor_id=competitor.id, activity_type=activity_type)
            for template in templates
        )
    ]


def _build_activity(
    competitor: Competitor,
    template: SimulationTemplate,
    *,
    now: datetime,
    event_id: str,
    company_id: str,
) -> CompetitorActivity:
    return CompetitorActivity(
        id=f"act_sim_{event_id}",
        company_id=company_id,
        competitor_id=competitor.id,
        competitor_name=competitor.name,
        activity_type=template.activity_type,
        channel=template.channel,
        title=template.title,
        summary=template.summary,
        url=template.url,
        content_excerpt=template.content_excerpt,
        occurred_at=now,
        detected_at=now,
        source=Provenance(system=SourceSystem.SIMULATED, ref_id=f"simulation:{event_id}"),
        is_mock=True,
        is_simulated=True,
        ingested_at=now,
    )


class SimulationService:
    def __init__(
        self,
        database: AsyncDatabase[Document],
        templates: Sequence[SimulationTemplate],
        *,
        random_source: Random | None = None,
    ) -> None:
        self.database = database
        self.templates = templates
        self.random_source = random_source or Random()

    async def simulate_activity(
        self,
        *,
        activity_type: ActivityType | None = None,
        competitor_id: str | None = None,
        company_id: str = "cmp_marketing_eye",
    ) -> CompetitorActivity:
        competitors = await CompetitorsRepository(self.database).list_for_company(
            company_id, limit=100
        )
        if competitor_id is not None:
            competitor = next((item for item in competitors if item.id == competitor_id), None)
            if competitor is None:
                raise ValidationError(f"Competitor {competitor_id} not found")
            if not competitor.is_fictional:
                raise ValidationError(SIMULATION_REAL_COMPETITOR_ERROR)
            templates = [
                template
                for template in self.templates
                if _template_matches(
                    template, competitor_id=competitor.id, activity_type=activity_type
                )
            ]
            if not templates:
                raise ValidationError("No simulation template is available for that request")
        else:
            options = _fictional_options(competitors, self.templates, activity_type)
            if not options:
                raise ValidationError("No fictional simulation template is available")
            competitor, templates = self.random_source.choice(options)

        template = self.random_source.choice(templates)
        event_id = uuid4().hex
        now = datetime.now(UTC)
        activity = _build_activity(
            competitor,
            template,
            now=now,
            event_id=event_id,
            company_id=company_id,
        )
        await CompetitorActivitiesRepository(self.database).upsert_by_source(activity)
        logger.info(
            "Created simulated activity %s",
            activity.id,
            extra={"ctx": {"activity_id": activity.id, "competitor_id": competitor.id}},
        )
        return activity


async def simulate_activity(
    database: AsyncDatabase[Document],
    templates: Sequence[SimulationTemplate],
    *,
    activity_type: ActivityType | None = None,
    competitor_id: str | None = None,
    company_id: str = "cmp_marketing_eye",
    random_source: Random | None = None,
) -> CompetitorActivity:
    return await SimulationService(
        database, templates, random_source=random_source
    ).simulate_activity(
        activity_type=activity_type,
        competitor_id=competitor_id,
        company_id=company_id,
    )
