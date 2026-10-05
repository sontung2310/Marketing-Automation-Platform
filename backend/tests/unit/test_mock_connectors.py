"""Each mock connector returns its agents-spec §8 receipt, marked as mock."""

import pytest

from app.connectors.mock import MOCK_CONNECTORS
from app.intelligence.models import ActionType

PAYLOADS: dict[ActionType, dict[str, object]] = {
    ActionType.SCHEDULE_SOCIAL_POST: {
        "channel": "LINKEDIN",
        "scheduled_for": "2026-10-12T09:00:00+11:00",
        "text": "Hi",
        "deliverable_id": "del_1",
    },
    ActionType.CREATE_CMS_DRAFT: {"title": "T", "body_markdown": "B", "slug": "t", "tags": []},
    ActionType.CREATE_EMAIL_DRAFT: {"to_name": None, "subject": "S", "body": "B"},
    ActionType.ADD_TO_CONTENT_CALENDAR: {"title": "T", "channel": None, "date": "2026-10-12"},
}
RECEIPTS: dict[ActionType, dict[str, object]] = {
    ActionType.SCHEDULE_SOCIAL_POST: {
        "status": "SCHEDULED",
        "channel": "LINKEDIN",
        "scheduled_for": "2026-10-12T09:00:00+11:00",
    },
    ActionType.CREATE_CMS_DRAFT: {
        "status": "DRAFT_CREATED",
        "preview_url": "https://cms.example/drafts/t",
    },
    ActionType.CREATE_EMAIL_DRAFT: {"status": "DRAFT_SAVED"},
    ActionType.ADD_TO_CONTENT_CALENDAR: {"status": "ADDED"},
}


@pytest.mark.parametrize("action_type", list(ActionType))
async def test_each_connector_returns_its_receipt(action_type: ActionType) -> None:
    receipt = await MOCK_CONNECTORS[action_type].execute(PAYLOADS[action_type])
    assert str(receipt.pop("receipt_id")).startswith("rcp_mock_")
    assert receipt == RECEIPTS[action_type] | {"mock": True}
