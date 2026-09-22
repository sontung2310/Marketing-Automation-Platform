"""Uvicorn entrypoint for the Marketing Intelligence MCP service."""

from starlette.applications import Starlette

from app.core.config import get_settings
from app.core.db import get_database
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.trends import TrendsRepository
from app.mcp_server.server import McpRepositories, build_mcp_app


def create_app() -> Starlette:
    """Compose repositories around the configured owned database."""

    settings = get_settings()
    database = get_database()
    repositories = McpRepositories(
        companies=CompaniesRepository(database),
        competitors=CompetitorsRepository(database),
        activities=CompetitorActivitiesRepository(database),
        trends=TrendsRepository(database),
        influencers=InfluencersRepository(database),
        recommendations=RecommendationsRepository(database),
    )
    return build_mcp_app(
        repositories,
        company_id=settings.default_company_id,
        host=settings.mcp_host,
        allowed_hosts=settings.mcp_allowed_hosts,
    )


app = create_app()
