"""Run intents shared by the router, the run service and the agents (agents-spec §5)."""

from enum import StrEnum


class Intent(StrEnum):
    # Strategy
    STRATEGY_SYNTHESIS = "STRATEGY_SYNTHESIS"  # the company-wide set, optionally focused
    TOPIC_RECOMMENDATION = "TOPIC_RECOMMENDATION"
    RESPONSE_PLAN = "RESPONSE_PLAN"
    WHY_IT_MATTERS = "WHY_IT_MATTERS"
    INFLUENCER_RECOMMENDATION = "INFLUENCER_RECOMMENDATION"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    COMPETITOR_QUESTION = "COMPETITOR_QUESTION"
    # Execution
    CREATE_SIMILAR = "CREATE_SIMILAR"
    FROM_RECOMMENDATION = "FROM_RECOMMENDATION"
    FREEFORM_DELIVERABLE = "FREEFORM_DELIVERABLE"
    INFLUENCER_OUTREACH = "INFLUENCER_OUTREACH"
    REVISE_DELIVERABLE = "REVISE_DELIVERABLE"
    # A chat message sent with an explicit agent, before the Step 6 classifier.
    CHAT = "CHAT"
