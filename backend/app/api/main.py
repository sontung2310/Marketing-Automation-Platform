"""FastAPI application factory. Run: uv run uvicorn app.api.main:app --reload"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import actions, feed, health
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.intelligence.startup import ensure_owned_indexes


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await ensure_owned_indexes()
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

    @app.exception_handler(RequestValidationError)
    async def request_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Malformed requests use the same envelope as domain errors (api-contract).
        error = {"code": "VALIDATION_ERROR", "message": "The request is not valid"}
        body = {"error": error | {"details": {"errors": jsonable_encoder(exc.errors())}}}
        return JSONResponse(status_code=422, content=body)

    app.include_router(health.router, prefix="/api")
    app.include_router(actions.router, prefix="/api")
    app.include_router(feed.router, prefix="/api")
    return app


app = create_app()
