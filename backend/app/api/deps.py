"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends

from app.connectors.mock import MOCK_CONNECTORS
from app.core.config import Settings, get_settings
from app.core.db import Database, get_database
from app.core.health import HealthChecker
from app.intelligence.repositories import ProposedActionsRepository
from app.orchestration.actions import ActionService
from app.orchestration.references import RunRepositories
from app.orchestration.router import Classifier, classify
from app.orchestration.run_api import RUN_AGENTS
from app.orchestration.run_service import RunService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_checker(settings: SettingsDep) -> HealthChecker:
    return HealthChecker(settings)


HealthCheckerDep = Annotated[HealthChecker, Depends(get_health_checker)]


DatabaseDep = Annotated[Database, Depends(get_database)]


def get_action_service(database: DatabaseDep) -> ActionService:
    # ponytail: mock connectors only (PoC); real ones register here by ActionType.
    return ActionService(ProposedActionsRepository(database), MOCK_CONNECTORS)


ActionServiceDep = Annotated[ActionService, Depends(get_action_service)]


def get_run_service(database: DatabaseDep) -> RunService:
    return RunService(RunRepositories.for_database(database), RUN_AGENTS)


RunServiceDep = Annotated[RunService, Depends(get_run_service)]


def get_classifier() -> Classifier:
    return classify


ClassifierDep = Annotated[Classifier, Depends(get_classifier)]
