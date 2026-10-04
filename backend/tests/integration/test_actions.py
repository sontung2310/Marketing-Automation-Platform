"""Scenario 5-D over HTTP: approve executes once, a discarded action can't be approved."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest

from app.api.main import app
from app.core.config import get_settings
from app.core.db import Database, get_database
from app.intelligence.models import ActionType, ProposedAction, ProposedActionStatus
from app.intelligence.repositories import ProposedActionsRepository
from evals.runtime import throwaway_database

pytestmark = pytest.mark.integration
NOW = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)


def action(action_id: str, action_type: ActionType, payload: dict[str, object]) -> ProposedAction:
    return ProposedAction(
        id=action_id,
        deliverable_id="del_1",
        action_type=action_type,
        summary="Mock action",
        payload=payload,
        status=ProposedActionStatus.PROPOSED,
        created_at=NOW,
        updated_at=NOW,
    )


CMS = action(
    "pac_cms",
    ActionType.CREATE_CMS_DRAFT,
    {"title": "A clearer plan", "body_markdown": "Body", "slug": "a-clearer-plan", "tags": []},
)
POST = action(
    "pac_post",
    ActionType.SCHEDULE_SOCIAL_POST,
    {
        "channel": "LINKEDIN",
        "scheduled_for": "2026-10-12T09:00:00+11:00",
        "text": "My view.",
        "deliverable_id": "del_1",
    },
)


@pytest.fixture
async def client() -> AsyncIterator[tuple[httpx.AsyncClient, Database]]:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")
    async with throwaway_database("ma_actions") as database:
        await ProposedActionsRepository(database).insert_many([CMS, POST])
        app.dependency_overrides[get_database] = lambda: database
        transport = httpx.ASGITransport(app=app)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
                yield http, database
        finally:
            app.dependency_overrides.clear()


async def test_approve_executes_once(client: tuple[httpx.AsyncClient, Database]) -> None:
    http, database = client
    response = await http.post("/api/actions/pac_cms/approve")
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["status"]) == ("pac_cms", "EXECUTED")
    receipt = body["receipt"]
    assert receipt["receipt_id"].startswith("rcp_mock_") and receipt["mock"] is True
    assert receipt["status"] == "DRAFT_CREATED"
    assert receipt["preview_url"] == "https://cms.example/drafts/a-clearer-plan"

    again = await http.post("/api/actions/pac_cms/approve")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "CONFLICT"
    stored = await database["proposed_actions"].find_one({"_id": "pac_cms"})
    assert stored is not None and stored["receipt"]["receipt_id"] == receipt["receipt_id"]


async def test_a_discarded_action_cant_be_approved(
    client: tuple[httpx.AsyncClient, Database],
) -> None:
    http, database = client
    discarded = await http.post("/api/actions/pac_post/discard")
    assert (discarded.status_code, discarded.json()["status"]) == (200, "DISCARDED")
    approve = await http.post("/api/actions/pac_post/approve")
    assert approve.status_code == 409
    stored = await database["proposed_actions"].find_one({"_id": "pac_post"})
    assert stored is not None and (stored["status"], stored["receipt"]) == ("DISCARDED", None)


async def test_unknown_action_is_not_found(client: tuple[httpx.AsyncClient, Database]) -> None:
    http, _ = client
    response = await http.post("/api/actions/pac_missing/approve")
    assert (response.status_code, response.json()["error"]["code"]) == (404, "NOT_FOUND")


async def test_an_approval_override_is_validated(
    client: tuple[httpx.AsyncClient, Database],
) -> None:
    http, database = client
    bad = await http.post(
        "/api/actions/pac_post/approve", json={"payload_overrides": {"scheduled_for": "soon"}}
    )
    assert (bad.status_code, bad.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    malformed = await http.post("/api/actions/pac_post/approve", json={"payload_overrides": 3})
    assert (malformed.status_code, malformed.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    stored = await database["proposed_actions"].find_one({"_id": "pac_post"})
    assert stored is not None and stored["status"] == "PROPOSED"

    moved = await http.post(
        "/api/actions/pac_post/approve",
        json={"payload_overrides": {"scheduled_for": "2026-10-13T10:00:00+11:00"}},
    )
    assert moved.status_code == 200
    assert moved.json()["receipt"]["scheduled_for"] == "2026-10-13T10:00:00+11:00"
