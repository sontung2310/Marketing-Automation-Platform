"""Serve the real Intelligence MCP in-process over a given database (evals and tests)."""

import asyncio
import socket
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

import uvicorn
from starlette.types import ASGIApp

from app.core import db
from app.core.config import get_settings
from app.core.db import Database
from app.mcp_server.server import McpRepositories, build_mcp_app

STARTUP_TIMEOUT_S = 5.0
STARTUP_POLL_S = 0.01


@asynccontextmanager
async def throwaway_database(prefix: str) -> AsyncIterator[Database]:
    """A uniquely named database on the configured cluster, dropped on exit."""
    name = f"{prefix}_{uuid4().hex[:12]}"
    try:
        yield db.get_client()[name]
    finally:
        await db.get_client().drop_database(name)


@asynccontextmanager
async def serve_mcp(
    database: Database, company_id: str, now: Callable[[], datetime] | None = None
) -> AsyncIterator[str]:
    """Serve the real MCP app over `database` on a free local port; yield its endpoint."""
    app = build_mcp_app(
        McpRepositories.for_database(database),
        company_id=company_id,
        now=now,
        allowed_hosts=get_settings().mcp_allowed_hosts,
    )
    async with serve_app(app) as base_url:
        yield f"{base_url}/mcp"


@asynccontextmanager
async def serve_app(app: ASGIApp) -> AsyncIterator[str]:
    """Serve an ASGI app on a free local port; yield its base URL."""
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
                raise TimeoutError("The in-process server did not start")
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=STARTUP_TIMEOUT_S)
