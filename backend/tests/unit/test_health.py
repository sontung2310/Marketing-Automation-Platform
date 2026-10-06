import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_health_checker
from app.api.main import create_app
from app.core.config import Settings
from app.core.health import HealthChecker


class StubChecker(HealthChecker):
    def __init__(self, *, mongo: bool, mcp: bool, openai_key: str | None) -> None:
        super().__init__(Settings(openai_api_key=openai_key))
        self._mongo, self._mcp = mongo, mcp

    async def mongo_ok(self) -> bool:
        return self._mongo

    async def mcp_ok(self) -> bool:
        return self._mcp


def _client(checker: HealthChecker) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_health_checker] = lambda: checker
    return TestClient(app)


def test_health_reports_all_dependencies_up() -> None:
    response = _client(StubChecker(mongo=True, mcp=True, openai_key="sk-test")).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongo": "ok", "mcp": "ok", "openai": "configured"}


def test_health_reports_down_dependencies_without_failing() -> None:
    response = _client(StubChecker(mongo=False, mcp=False, openai_key=None)).get("/api/health")

    assert response.status_code == 200
    assert response.json()["mongo"] == "down"
    assert response.json()["mcp"] == "down"
    assert response.json()["openai"] == "missing"


@pytest.mark.parametrize(
    ("status", "up"),
    [(200, True), (405, True), (406, True), (403, False), (404, False), (421, False), (503, False)],
)
async def test_mcp_probe_treats_missing_or_failing_endpoints_as_down(
    status: int, up: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client(transport=transport, **kw))

    assert await HealthChecker(Settings(mcp_url="http://mcp.test/mcp")).mcp_ok() is up
