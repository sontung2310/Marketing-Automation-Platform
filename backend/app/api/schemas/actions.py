"""Request bodies for the proposed-action endpoints (api-contract, Proposed actions)."""

from pydantic import BaseModel, ConfigDict


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_overrides: dict[str, object] | None = None
