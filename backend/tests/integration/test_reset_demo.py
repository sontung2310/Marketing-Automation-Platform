"""reset_demo_state wipes one company's run history and leaves the rest of the seed alone."""

from datetime import UTC, datetime

import pytest

from app.core.config import get_settings
from app.intelligence.models import (
    ActionType,
    ActivityType,
    AgentName,
    Channel,
    CompetitorActivity,
    Deliverable,
    ProposedAction,
    ProposedActionStatus,
    Provenance,
    Recommendation,
    RecommendationEvidence,
    RecommendationStatus,
    Run,
    RunStatus,
    Session,
    SourceSystem,
)
from app.intelligence.repositories.activities import CompetitorActivitiesRepository
from app.intelligence.repositories.deliverables import DeliverablesRepository
from app.intelligence.repositories.proposed_actions import ProposedActionsRepository
from app.intelligence.repositories.recommendations import RecommendationsRepository
from app.intelligence.repositories.runs import RunsRepository
from app.intelligence.repositories.sessions import SessionsRepository
from app.pipelines.seed.loader import load_seed_bundle
from app.pipelines.seed.reset import reset_demo_state
from app.pipelines.seed.writer import seed_database
from evals.runtime import throwaway_database

pytestmark = pytest.mark.integration


async def test_reset_wipes_history_and_reseeds_to_the_same_baseline() -> None:
    if get_settings().mongodb_uri is None:
        pytest.skip("MONGODB_URI is not configured")

    # seed_database revalidates against real time, so the bundle is rebased to it too
    # (same pattern as test_seed.py's test_seed_is_idempotent_and_meets_minimums).
    now = datetime.now(UTC)

    async with throwaway_database("ma_reset_test") as database:
        bundle = load_seed_bundle(now=now)
        company_id = bundle.companies[0].id
        other_company_id = "cmp_other"
        competitor_id = bundle.competitors[0].id
        await seed_database(database, bundle)
        fresh_counts = {
            name: await database[name].count_documents({})
            for name in ("companies", "competitors", "competitor_activities", "trends")
        }

        session = Session(id="ses_demo", company_id=company_id, created_at=now)
        run = Run(
            id="run_demo",
            session_id=session.id,
            agent=AgentName.EXECUTION,
            intent="CHAT",
            status=RunStatus.SUCCEEDED,
            started_at=now,
            finished_at=now,
        )
        recommendation = Recommendation(
            id="rec_demo",
            run_id=run.id,
            session_id=session.id,
            ordinal=1,
            kind="MONITOR",
            title="Watch it",
            rationale="Because.",
            priority="LOW",
            evidence=[RecommendationEvidence(id="trd_1", kind="trend", note="Rising")],
            next_action=None,
            status=RecommendationStatus.OPEN,
        )
        deliverable = Deliverable(
            id="del_demo",
            run_id=run.id,
            type="LINKEDIN_POST",
            title="A post",
            body_markdown="Body",
            word_count=1,
        )
        action = ProposedAction(
            id="pac_demo",
            deliverable_id=deliverable.id,
            action_type=ActionType.SCHEDULE_SOCIAL_POST,
            summary="Post it",
            payload={},
            status=ProposedActionStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        simulated = CompetitorActivity(
            _id="act_sim_demo",
            company_id=company_id,
            competitor_id=competitor_id,
            competitor_name="Competitor",
            activity_type=ActivityType.SOCIAL_POST,
            channel=Channel.LINKEDIN,
            title="A simulated post",
            summary="Simulated for the demo.",
            url=None,
            occurred_at=now,
            detected_at=now,
            source=Provenance(system=SourceSystem.SIMULATED, ref_id="sim_demo"),
            is_mock=False,
            is_simulated=True,
            ingested_at=now,
        )
        # A session from another company must survive this company's reset.
        other_session = Session(id="ses_other", company_id=other_company_id, created_at=now)

        await SessionsRepository(database).insert_many([session, other_session])
        await RunsRepository(database).insert_many([run])
        await RecommendationsRepository(database).insert_many([recommendation])
        await DeliverablesRepository(database).insert_many([deliverable])
        await ProposedActionsRepository(database).insert_many([action])
        await CompetitorActivitiesRepository(database).insert_many([simulated])

        counts = await reset_demo_state(database, company_id)

        assert counts.sessions == 1
        assert counts.runs == 1
        assert counts.recommendations == 1
        assert counts.deliverables == 1
        assert counts.proposed_actions == 1
        assert counts.simulated_activities == 1
        assert await database["sessions"].count_documents({}) == 1  # the other company's
        assert await database["sessions"].find_one({"_id": "ses_other"}) is not None
        for name in ("runs", "recommendations", "deliverables", "proposed_actions"):
            assert await database[name].count_documents({}) == 0
        assert await database["competitor_activities"].find_one({"_id": "act_sim_demo"}) is None

        reseeded = await seed_database(database, load_seed_bundle(now=now))
        reseeded_counts = {
            name: await database[name].count_documents({})
            for name in ("companies", "competitors", "competitor_activities", "trends")
        }
        assert reseeded_counts == fresh_counts
        assert reseeded.collections["companies"].total == len(bundle.companies)
