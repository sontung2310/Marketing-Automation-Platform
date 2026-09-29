"""Uvicorn entrypoint for the Marketing Intelligence MCP service."""

from starlette.applications import Starlette

from app.core.config import get_settings
from app.core.db import get_database
from app.mcp_server.server import McpRepositories, build_mcp_app


def create_app() -> Starlette:
    """Compose repositories around the configured owned database."""

    settings = get_settings()
    return build_mcp_app(
        McpRepositories.for_database(get_database()),
        company_id=settings.default_company_id,
        allowed_hosts=settings.mcp_allowed_hosts,
    )


app = create_app()
