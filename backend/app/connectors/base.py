"""The Connector protocol: a real integration replaces a mock without touching the agents."""

from typing import Protocol


class Connector(Protocol):
    async def execute(self, payload: dict[str, object]) -> dict[str, object]:
        """Run one approved action with its validated payload and return the receipt."""
        ...
