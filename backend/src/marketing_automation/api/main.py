"""FastAPI application factory. Run: uv run uvicorn marketing_automation.api.main:app --reload"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from marketing_automation.api.routes import health
from marketing_automation.core.config import get_settings
from marketing_automation.core.errors import DomainError
from marketing_automation.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Marketing Automation Platform API", version="0.1.0")
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

    app.include_router(health.router, prefix="/api")
    return app


app = create_app()
