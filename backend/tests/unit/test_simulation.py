from typing import cast

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core.errors import ValidationError
from app.intelligence.models import ActivityType, Competitor, Provenance, SourceSystem
from app.intelligence.repositories.base import Document
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.simulation import SIMULATION_REAL_COMPETITOR_ERROR, SimulationService


class _Cursor:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents

    def limit(self, _limit: int) -> "_Cursor":
        return self

    def __aiter__(self) -> "_Cursor":
        self.index = 0
        return self

    async def __anext__(self) -> Document:
        if self.index >= len(self.documents):
            raise StopAsyncIteration
        document = self.documents[self.index]
        self.index += 1
        return document


class _Result:
    upserted_id = "inserted"
    modified_count = 0


class _Collection:
    def __init__(self, documents: list[Document]) -> None:
        self.documents = documents
        self.writes = 0

    def find(self, query: Document) -> _Cursor:
        company_id = query.get("company_id")
        if isinstance(company_id, str):
            return _Cursor(
                [
                    document
                    for document in self.documents
                    if document.get("company_id") == company_id
                ]
            )
        return _Cursor(self.documents)

    async def update_one(self, _query: Document, _update: Document, *, upsert: bool) -> _Result:
        assert upsert is True
        self.writes += 1
        return _Result()


class _Database:
    def __init__(self, documents: list[Document]) -> None:
        self.collections = {
            "competitors": _Collection(documents),
            "competitor_activities": _Collection([]),
        }

    def __getitem__(self, name: str) -> _Collection:
        return self.collections[name]


def _competitors() -> list[Document]:
    return [
        Competitor(
            id="cpt_lyfe_marketing",
            company_id="cmp_marketing_eye",
            name="Lyfe Marketing",
            website="https://www.lyfemarketing.com/",
            is_fictional=False,
            source=Provenance(system=SourceSystem.COMPETITORSCOPE, ref_id="lyfe"),
            is_mock=False,
        ).model_dump(by_alias=True, mode="python"),
        Competitor(
            id="cpt_brightlane",
            company_id="cmp_marketing_eye",
            name="Brightlane Marketing",
            website="https://brightlane.example/",
            is_fictional=True,
            source=Provenance(system=SourceSystem.MOCK_SEED, ref_id="brightlane"),
            is_mock=True,
        ).model_dump(by_alias=True, mode="python"),
    ]


@pytest.mark.asyncio
async def test_simulation_rejects_real_and_creates_distinct_fictional_events() -> None:
    database = _Database(_competitors())
    templates = load_seed_bundle().simulation_templates
    service = SimulationService(cast(AsyncDatabase[Document], database), templates)

    with pytest.raises(ValidationError, match=SIMULATION_REAL_COMPETITOR_ERROR):
        await service.simulate_activity(competitor_id="cpt_lyfe_marketing")

    first = await service.simulate_activity(
        competitor_id="cpt_brightlane", activity_type=ActivityType.SOCIAL_POST
    )
    second = await service.simulate_activity(
        competitor_id="cpt_brightlane", activity_type=ActivityType.SOCIAL_POST
    )

    assert first.competitor_id == "cpt_brightlane"
    assert first.is_mock is True
    assert first.is_simulated is True
    assert first.source.system is SourceSystem.SIMULATED
    assert first.source.ref_id != second.source.ref_id
    assert database.collections["competitor_activities"].writes == 2


@pytest.mark.asyncio
async def test_random_simulation_never_selects_real_competitor() -> None:
    database = _Database(_competitors())
    templates = load_seed_bundle().simulation_templates
    service = SimulationService(cast(AsyncDatabase[Document], database), templates)

    activity = await service.simulate_activity()

    assert activity.competitor_id == "cpt_brightlane"


@pytest.mark.asyncio
async def test_cross_tenant_competitor_is_not_visible_to_simulation() -> None:
    other_tenant = Competitor(
        id="cpt_other_tenant",
        company_id="cmp_other",
        name="Other Fictional",
        website="https://other.example/",
        is_fictional=True,
        source=Provenance(system=SourceSystem.MOCK_SEED, ref_id="other"),
        is_mock=True,
    ).model_dump(by_alias=True, mode="python")
    database = _Database([*_competitors(), other_tenant])
    service = SimulationService(
        cast(AsyncDatabase[Document], database), load_seed_bundle().simulation_templates
    )

    with pytest.raises(ValidationError, match="not found"):
        await service.simulate_activity(
            competitor_id="cpt_other_tenant", company_id="cmp_marketing_eye"
        )

    assert database.collections["competitor_activities"].writes == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("activity_type", list(ActivityType))
async def test_every_activity_type_has_a_fictional_template(activity_type: ActivityType) -> None:
    database = _Database(_competitors())
    templates = load_seed_bundle().simulation_templates
    competitor_id = next(
        template.competitor_id for template in templates if template.activity_type == activity_type
    )
    service = SimulationService(cast(AsyncDatabase[Document], database), templates)

    activity = await service.simulate_activity(
        competitor_id=competitor_id, activity_type=activity_type
    )

    assert activity.activity_type is activity_type
    assert activity.is_simulated is True
