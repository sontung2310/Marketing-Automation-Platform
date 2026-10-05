"""POST /api/actions/{action_id}/approve and /discard: validate and delegate."""

from fastapi import APIRouter

from app.api.deps import ActionServiceDep
from app.api.schemas.actions import ApproveRequest

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/{action_id}/approve")
async def approve(
    action_id: str, service: ActionServiceDep, body: ApproveRequest | None = None
) -> dict[str, object]:
    overrides = body.payload_overrides if body else None
    return (await service.approve(action_id, overrides)).model_dump(mode="json")


@router.post("/{action_id}/discard")
async def discard(action_id: str, service: ActionServiceDep) -> dict[str, object]:
    return (await service.discard(action_id)).model_dump(mode="json")
