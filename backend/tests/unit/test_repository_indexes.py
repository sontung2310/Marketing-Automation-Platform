from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.companies import CompaniesRepository
from app.intelligence.repositories.competitors import CompetitorsRepository
from app.intelligence.repositories.deliverables import DeliverablesRepository
from app.intelligence.repositories.influencers import InfluencersRepository
from app.intelligence.repositories.proposed_actions import ProposedActionsRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.runs import RunsRepository
from app.intelligence.repositories.sessions import SessionsRepository
from app.intelligence.repositories.trends import TrendsRepository


def test_repository_collection_names_are_explicit() -> None:
    repositories = (
        CompaniesRepository,
        CompetitorsRepository,
        CompetitorActivitiesRepository,
        TrendsRepository,
        InfluencersRepository,
        SessionsRepository,
        RunsRepository,
        RecommendationsRepository,
        DeliverablesRepository,
        ProposedActionsRepository,
    )

    assert [repository.collection_name for repository in repositories] == [
        "companies",
        "competitors",
        "competitor_activities",
        "trends",
        "influencers",
        "sessions",
        "runs",
        "recommendations",
        "deliverables",
        "proposed_actions",
    ]
