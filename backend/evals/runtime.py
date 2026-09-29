"""Serve the real Intelligence MCP in-process over a given database (evals and live tests)."""

import asyncio
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn

from app.core.config import get_settings
from app.core.db import Database
from app.intelligence.repositories import (
    CompaniesRepository,
    CompetitorActivitiesRepository,
    CompetitorsRepository,
    InfluencersRepository,
    RecommendationsRepository,
    TrendsRepository,
)
from app.mcp_server.server import McpRepositories, build_mcp_app

STARTUP_TIMEOUT_S = 5.0
STARTUP_POLL_S = 0.01


@asynccontextmanager
async def serve_mcp(database: Database, company_id: str) -> AsyncIterator[str]:
    """Yield the MCP endpoint URL on a free local port; stop the server on exit."""
    repositories = McpRepositories(
        companies=CompaniesRepository(database),
        competitors=CompetitorsRepository(database),
        activities=CompetitorActivitiesRepository(database),
        trends=TrendsRepository(database),
        influencers=InfluencersRepository(database),
        recommendations=RecommendationsRepository(database),
    )
    app = build_mcp_app(
        repositories, company_id=company_id, allowed_hosts=get_settings().mcp_allowed_hosts
    )
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False, log_level="warning")
        )
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            # uvicorn exposes only a `started` flag, so poll it for a bounded time.
            for _ in range(int(STARTUP_TIMEOUT_S / STARTUP_POLL_S)):
                if server.started:
                    break
                await asyncio.sleep(STARTUP_POLL_S)
            else:
                raise TimeoutError("The in-process MCP server did not start")
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=STARTUP_TIMEOUT_S)
