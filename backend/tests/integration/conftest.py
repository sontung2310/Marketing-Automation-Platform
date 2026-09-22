import pytest

from app.core import db


@pytest.fixture(autouse=True)
async def clear_mongo_client_between_event_loops() -> None:
    """AsyncMongoClient is bound to one pytest event loop at a time."""

    yield
    if db.get_client.cache_info().currsize:
        await db.get_client().close()
        db.get_client.cache_clear()
