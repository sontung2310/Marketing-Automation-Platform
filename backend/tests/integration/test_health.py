import httpx
import pytest

from app.api.main import app
from app.core import db

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def clear_cached_mongo_client() -> None:
    yield
    if db.get_client.cache_info().currsize:
        await db.get_client().close()
        db.get_client.cache_clear()


async def test_health_reports_configured_mongo_as_up() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["mongo"] == "ok"
