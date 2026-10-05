"""The approve/discard state machine: only PROPOSED moves, and a connector error is FAILED."""

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from app.connectors.base import Connector
from app.connectors.mock import MOCK_CONNECTORS
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.intelligence.models import ActionType, ProposedAction, ProposedActionStatus
from app.intelligence.repositories import ProposedActionsRepository
from app.orchestration.actions import ActionService

NOW = datetime(2026, 10, 9, 3, 0, tzinfo=UTC)


class MemoryActions:
    """The two repository calls the service makes, over a dict."""

    def __init__(self, *actions: ProposedAction) -> None:
        self.rows = {a.id: a for a in actions}

    async def get(self, action_id: str) -> ProposedAction | None:
        return self.rows.get(action_id)

    async def transition(
        self, action_id: str, from_status: ProposedActionStatus, update: dict[str, object]
    ) -> ProposedAction | None:
        row = self.rows.get(action_id)
        if row is None or row.status is not from_status:
            return None
        self.rows[action_id] = row.model_copy(update=update)
        return self.rows[action_id]


def proposed(status: ProposedActionStatus = ProposedActionStatus.PROPOSED) -> ProposedAction:
    return ProposedAction(
        id="pac_1",
        deliverable_id="del_1",
        action_type=ActionType.SCHEDULE_SOCIAL_POST,
        summary="Schedule on LinkedIn",
        payload={
            "channel": "LINKEDIN",
            "scheduled_for": "2026-10-12T09:00:00+11:00",
            "text": "My view.",
            "deliverable_id": "del_1",
        },
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def service(memory: MemoryActions, connectors: Any = MOCK_CONNECTORS) -> ActionService:
    return ActionService(cast(ProposedActionsRepository, memory), connectors, clock=lambda: NOW)


async def test_approve_executes_once() -> None:
    memory = MemoryActions(proposed())
    done = await service(memory).approve("pac_1")
    assert done.status is ProposedActionStatus.EXECUTED
    assert done.receipt is not None and done.receipt["status"] == "SCHEDULED"
    with pytest.raises(ConflictError):
        await service(memory).approve("pac_1")
    assert memory.rows["pac_1"].receipt == done.receipt  # unchanged by the second approve


async def test_an_override_is_validated_and_applied() -> None:
    memory = MemoryActions(proposed())
    with pytest.raises(ValidationError):
        await service(memory).approve("pac_1", {"scheduled_for": "tomorrow"})
    assert memory.rows["pac_1"].status is ProposedActionStatus.PROPOSED
    done = await service(memory).approve("pac_1", {"scheduled_for": "2026-10-13T10:00:00+11:00"})
    assert done.payload["scheduled_for"] == "2026-10-13T10:00:00+11:00"


async def test_discarded_cannot_be_approved_and_unknown_is_not_found() -> None:
    memory = MemoryActions(proposed())
    assert (await service(memory).discard("pac_1")).status is ProposedActionStatus.DISCARDED
    with pytest.raises(ConflictError):
        await service(memory).approve("pac_1")
    with pytest.raises(ConflictError):
        await service(memory).discard("pac_1")
    with pytest.raises(NotFoundError):
        await service(memory).approve("pac_missing")


class BrokenConnector:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("secret upstream detail")


async def test_a_connector_error_is_failed_without_leaking_detail() -> None:
    memory = MemoryActions(proposed())
    connectors: dict[ActionType, Connector] = {ActionType.SCHEDULE_SOCIAL_POST: BrokenConnector()}
    failed = await service(memory, connectors).approve("pac_1")
    assert failed.status is ProposedActionStatus.FAILED and failed.receipt is None
    assert failed.error is not None and "secret" not in failed.error


async def test_a_past_schedule_is_rejected() -> None:
    memory = MemoryActions(proposed())
    with pytest.raises(ValidationError):
        await service(memory).approve("pac_1", {"scheduled_for": "2026-10-01T09:00:00+10:00"})
    assert memory.rows["pac_1"].status is ProposedActionStatus.PROPOSED


class CancelledConnector:
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        raise asyncio.CancelledError


async def test_a_cancelled_connector_still_settles_the_action() -> None:
    memory = MemoryActions(proposed())
    connectors: dict[ActionType, Connector] = {
        ActionType.SCHEDULE_SOCIAL_POST: CancelledConnector()
    }
    with pytest.raises(asyncio.CancelledError):
        await service(memory, connectors).approve("pac_1")
    assert memory.rows["pac_1"].status is ProposedActionStatus.FAILED


async def test_an_override_cannot_move_the_action_to_another_deliverable() -> None:
    memory = MemoryActions(proposed())
    done = await service(memory).approve("pac_1", {"deliverable_id": "del_other"})
    assert done.payload["deliverable_id"] == "del_1"
