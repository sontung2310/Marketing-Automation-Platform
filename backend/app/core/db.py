"""Shared async MongoDB client with timezone-aware datetimes for every consumer."""

from functools import lru_cache

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.core.errors import UpstreamUnavailableError

Document = dict[str, object]
# Lets layers that may not import pymongo (e.g. orchestration) name a database.
Database = AsyncDatabase[Document]


@lru_cache
def get_client() -> AsyncMongoClient[Document]:
    settings = get_settings()
    if settings.mongodb_uri is None:
        raise UpstreamUnavailableError("MONGODB_URI is not configured")
    return AsyncMongoClient(
        # Keep datetimes aware across repositories, pipelines and health checks.
        settings.mongodb_uri.get_secret_value(),
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    )


def get_database() -> AsyncDatabase[Document]:
    return get_client()[get_settings().mongodb_database]


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
    except Exception:
        return False
    return True
