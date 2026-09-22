from collections.abc import AsyncIterator

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.intelligence.repositories.base import Document
from app.intelligence.repositories.indexes import ensure_indexes
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.simulation import SimulationService

pytestmark = pytest.mark.integration


@pytest.fixture
async def simulation_database() -> AsyncIterator[AsyncDatabase[Document]]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    database_name = "ma_simulation_service_test"
    database = db.get_client()[database_name]
    await db.get_client().drop_database(database_name)
    yield database
    await db.get_client().drop_database(database_name)
    await db.get_client().close()
    db.get_client.cache_clear()


async def test_simulation_writes_owned_events_and_is_source_safe(
    simulation_database: AsyncDatabase[Document],
) -> None:
    await ensure_indexes(simulation_database)
    await simulation_database["competitors"].insert_many(
        [
            {
                "_id": "cpt_lyfe_marketing",
                "company_id": "cmp_marketing_eye",
                "name": "Lyfe Marketing",
                "website": "https://www.lyfemarketing.com/",
                "is_fictional": False,
                "social": {},
                "executives": [],
                "source": {"system": "COMPETITORSCOPE", "ref_id": "lyfe"},
                "is_mock": False,
            },
            {
                "_id": "cpt_brightlane",
                "company_id": "cmp_marketing_eye",
                "name": "Brightlane Marketing",
                "website": "https://brightlane.example/",
                "is_fictional": True,
                "social": {},
                "executives": [],
                "source": {"system": "MOCK_SEED", "ref_id": "brightlane"},
                "is_mock": True,
            },
        ]
    )
    before = await simulation_database["competitors"].count_documents({})
    service = SimulationService(
        simulation_database,
        load_seed_bundle().simulation_templates,
    )

    activity = await service.simulate_activity()

    assert activity.competitor_id == "cpt_brightlane"
    assert activity.is_simulated is True
    assert await simulation_database["competitor_activities"].count_documents({}) == 1
    assert await simulation_database["competitors"].count_documents({}) == before
