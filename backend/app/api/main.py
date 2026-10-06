"""FastAPI application factory. Run: uv run uvicorn app.api.main:app --reload"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.applications import Starlette

from app.api.routes import actions, feed, health, runs
from app.core.config import Settings, get_settings
from app.core.db import get_database
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.intelligence.startup import ensure_owned_indexes
from app.mcp_server.server import McpRepositories, build_mcp_app

logger = logging.getLogger(__name__)


def mcp_app_for(settings: Settings) -> Starlette:
    return build_mcp_app(
        McpRepositories.for_database(get_database()),
        company_id=settings.default_company_id,
        allowed_hosts=settings.mcp_allowed_hosts,
        stateless=True,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    # The Marketing Intelligence MCP rides along in the API process (Vercel has no second
    # long-lived service); agents still reach it over HTTP at MCP_URL, so layering holds.
    mcp_app = mcp_app_for(settings) if settings.mongodb_uri is not None else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await ensure_owned_indexes()
        if mcp_app is None:
            yield
            return
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(title="Marketing Automation Platform API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        body = {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}
        return JSONResponse(status_code=exc.http_status, content=body)

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Anything unhandled still speaks the envelope, so the UI can show it (api-contract).
        logger.exception("Unhandled API error", exc_info=exc)
        body = {"error": {"code": "INTERNAL", "message": "Unexpected server error", "details": {}}}
        return JSONResponse(status_code=500, content=body)

    @app.exception_handler(RequestValidationError)
    async def request_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Malformed requests use the same envelope as domain errors (api-contract).
        error = {"code": "VALIDATION_ERROR", "message": "The request is not valid"}
        body = {"error": error | {"details": {"errors": jsonable_encoder(exc.errors())}}}
        return JSONResponse(status_code=422, content=body)

    app.include_router(health.router, prefix="/api")
    app.include_router(actions.router, prefix="/api")
    app.include_router(feed.router, prefix="/api")
    app.include_router(runs.router, prefix="/api")
    if mcp_app is not None:
        app.router.routes.extend(mcp_app.routes)  # serves /mcp
    return app


app = create_app()
