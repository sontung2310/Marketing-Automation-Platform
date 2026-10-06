"""Dependency health probes used by GET /api/health."""

from typing import Literal

import httpx
from pydantic import BaseModel

from app.core import db
from app.core.config import Settings

MCP_ALIVE_REFUSALS = {400, 405, 406}


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
            # A stateless MCP answers a GET with a stream that stays open, so read the
            # headers only. 400/405/406 are a live MCP refusing a bare GET; 403, 404 or
            # 421 (host not allowed) mean agents cannot use it.
            async with (
                httpx.AsyncClient(timeout=1.5) as client,
                client.stream("GET", self._settings.mcp_url) as response,
            ):
                return response.is_success or response.status_code in MCP_ALIVE_REFUSALS
        except httpx.HTTPError:
            return False

    async def report(self) -> HealthReport:
        return HealthReport(
            mongo="ok" if await self.mongo_ok() else "down",
            mcp="ok" if await self.mcp_ok() else "down",
            openai="configured" if self._settings.openai_api_key else "missing",
        )
