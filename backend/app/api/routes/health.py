"""GET /api/health."""

from fastapi import APIRouter

from app.api.deps import HealthCheckerDep
from app.core.health import HealthReport

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health(checker: HealthCheckerDep) -> HealthReport:
    return await checker.report()
