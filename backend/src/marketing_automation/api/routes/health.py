"""GET /api/health."""

from fastapi import APIRouter

from marketing_automation.api.deps import HealthCheckerDep
from marketing_automation.core.health import HealthReport

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health(checker: HealthCheckerDep) -> HealthReport:
    return await checker.report()
