"""Best-effort startup wiring for owned collection indexes."""

import logging

from app.core import db
from app.core.config import get_settings
from app.intelligence.repositories.indexes import ensure_indexes

logger = logging.getLogger(__name__)


async def ensure_owned_indexes() -> None:
    """Create owned indexes when Mongo is configured without blocking health startup."""

    if get_settings().mongodb_uri is None:
        return
    try:
        await ensure_indexes(db.get_database())
    except Exception as exc:  # pragma: no cover - depends on remote Mongo availability
        logger.warning("owned Mongo indexes unavailable at startup", extra={"error": str(exc)})
