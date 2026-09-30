"""Trigger reference resolution and sessions against a seeded database."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pymongo.asynchronous.database import AsyncDatabase

from app.core import db
from app.core.config import get_settings
from app.core.db import Document
from app.core.errors import NotFoundError
from app.orchestration.references import RunRepositories, open_session, resolve_trigger
from app.orchestration.routing import Trigger, TriggerAction, TriggerKind
from evals.fixture import install_fixture, load_fixture

pytestmark = pytest.mark.integration
COMPANY = "cmp_marketing_eye"


async def test_feed_trigger_resolves_to_the_company_activity(
    seeded_database: AsyncDatabase[Document],
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    (activity,) = await repositories.activities.search_for_company(
        COMPANY, detected_since=datetime(2000, 1, 1, tzinfo=UTC), limit=1
    )
    trigger = Trigger(
        kind=TriggerKind.FEED_ACTION, ref_id=activity.id, action=TriggerAction.RESPONSE_PLAN
    )
    record = await resolve_trigger(repositories, trigger, COMPANY)
    assert record["id"] == activity.id  # same key shape as MCP results


@pytest.mark.parametrize("company", [COMPANY, "cmp_someone_else"])
async def test_unknown_or_foreign_reference_is_not_found(
    seeded_database: AsyncDatabase[Document], company: str
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    (trend,) = await repositories.trends.search_for_company(COMPANY, limit=1)
    ref = "trd_missing" if company == COMPANY else trend.id
    trigger = Trigger(kind=TriggerKind.TREND, ref_id=ref, action=TriggerAction.USE_TREND)
    with pytest.raises(NotFoundError):
        await resolve_trigger(repositories, trigger, company)


async def test_sessions_are_created_then_reused_per_company(
    seeded_database: AsyncDatabase[Document],
) -> None:
    repositories = RunRepositories.for_database(seeded_database)
    created = await open_session(repositories, COMPANY, None)
    assert (await open_session(repositories, COMPANY, created.id)).id == created.id
    with pytest.raises(NotFoundError):
        await open_session(repositories, "cmp_someone_else", created.id)


async def test_eval_fixture_installs_shifted_to_now() -> None:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    fixture = load_fixture("intelligence_v1")
    name = f"ma_fixture_{uuid4().hex[:12]}"
    database = db.get_client()[name]
    try:
        await install_fixture(database, fixture)
        assert await database["competitor_activities"].count_documents({}) == len(
            fixture.competitor_activities
        )
        stale = await database["competitor_activities"].find_one({"_id": "act_fx_stale_01"})
        assert stale is not None and isinstance(stale["detected_at"], datetime)
        age = datetime.now(UTC) - stale["detected_at"]
        assert 60 <= age.days <= 80  # authored ~70 days before the snapshot
    finally:
        await db.get_client().drop_database(name)
