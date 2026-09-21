"""Dependency health probes used by GET /api/health."""

from typing import Literal

import httpx
from pydantic import BaseModel

from app.core import db
from app.core.config import Settings


class HealthReport(BaseModel):
    status: Literal["ok"] = "ok"
    mongo: Literal["ok", "down"]
    mcp: Literal["ok", "down"]
    openai: Literal["configured", "missing"]


class HealthChecker:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def mongo_ok(self) -> bool:
        return await db.ping()

    async def mcp_ok(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                await client.get(self._settings.mcp_url)
        except httpx.HTTPError:
            return False
        return True

    async def report(self) -> HealthReport:
        return HealthReport(
            mongo="ok" if await self.mongo_ok() else "down",
            mcp="ok" if await self.mcp_ok() else "down",
            openai="configured" if self._settings.openai_api_key else "missing",
        )
