"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.health import HealthChecker

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_checker(settings: SettingsDep) -> HealthChecker:
    return HealthChecker(settings)


HealthCheckerDep = Annotated[HealthChecker, Depends(get_health_checker)]
