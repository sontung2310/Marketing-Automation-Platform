"""Shared async MongoDB client. Imported only by repositories, pipeline sources and health."""

from functools import lru_cache

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import get_settings
from app.core.errors import UpstreamUnavailableError

Document = dict[str, object]


@lru_cache
def get_client() -> AsyncMongoClient[Document]:
    settings = get_settings()
    if settings.mongodb_uri is None:
        raise UpstreamUnavailableError("MONGODB_URI is not configured")
    return AsyncMongoClient(
        settings.mongodb_uri.get_secret_value(), serverSelectionTimeoutMS=5000, tz_aware=True
    )


def get_database() -> AsyncDatabase[Document]:
    return get_client()[get_settings().mongodb_database]


async def ping() -> bool:
    try:
        await get_client().admin.command("ping")
    except Exception:
        return False
    return True
