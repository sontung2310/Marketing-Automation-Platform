import pytest

from app.core import db

pytestmark = pytest.mark.integration


async def test_mongo_ping_against_configured_cluster() -> None:
    assert await db.ping()
