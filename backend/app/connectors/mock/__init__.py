"""Mock connectors (agents-spec §8): receipts only, nothing leaves the platform."""

from dataclasses import dataclass

from ulid import ULID

from app.connectors.base import Connector
from app.intelligence.models import ActionType


def receipt(status: str, **fields: object) -> dict[str, object]:
    return {"receipt_id": f"rcp_mock_{ULID()}", "status": status, "mock": True, **fields}


@dataclass(frozen=True)
class MockSocialScheduler:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        return receipt(
            "SCHEDULED", channel=payload["channel"], scheduled_for=payload["scheduled_for"]
        )


@dataclass(frozen=True)
class MockCms:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        return receipt("DRAFT_CREATED", preview_url=f"https://cms.example/drafts/{payload['slug']}")


@dataclass(frozen=True)
class MockEmail:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        return receipt("DRAFT_SAVED")


@dataclass(frozen=True)
class MockCalendar:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        return receipt("ADDED")


MOCK_CONNECTORS: dict[ActionType, Connector] = {
    ActionType.SCHEDULE_SOCIAL_POST: MockSocialScheduler(),
    ActionType.CREATE_CMS_DRAFT: MockCms(),
    ActionType.CREATE_EMAIL_DRAFT: MockEmail(),
    ActionType.ADD_TO_CONTENT_CALENDAR: MockCalendar(),
}
