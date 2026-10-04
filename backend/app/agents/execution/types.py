"""The deliverable type each Execution trigger fixes in code (specs §6, agents-spec §7)."""

from collections.abc import Callable, Mapping

from app.agents.common.intents import Intent
from app.core.errors import ValidationError
from app.intelligence.models import ActivityType, Channel, DeliverableType

SIMILAR_TYPES: dict[ActivityType, DeliverableType] = {
    ActivityType.NEW_BLOG: DeliverableType.BLOG_DRAFT,
    ActivityType.EXECUTIVE_POST: DeliverableType.CEO_POST,
}
# A similar social post stays on the competitor's channel.
SOCIAL_POST_TYPES: dict[Channel, DeliverableType] = {
    Channel.LINKEDIN: DeliverableType.LINKEDIN_POST,
    Channel.X: DeliverableType.X_POST,
    Channel.INSTAGRAM: DeliverableType.INSTAGRAM_POST,
}

Record = Mapping[str, object]


def similar_type(activity: Record) -> DeliverableType | None:
    activity_type = ActivityType(str(activity["activity_type"]))
    if activity_type is ActivityType.SOCIAL_POST:
        return SOCIAL_POST_TYPES.get(Channel(str(activity["channel"])))
    return SIMILAR_TYPES.get(activity_type)


def recommended_type(recommendation: Record) -> DeliverableType | None:
    next_action = recommendation.get("next_action")
    if not isinstance(next_action, Mapping):
        return None
    return DeliverableType(str(next_action["deliverable_type"]))


RESOLVERS: dict[Intent, Callable[[Record], DeliverableType | None]] = {
    Intent.CREATE_SIMILAR: similar_type,
    Intent.FROM_RECOMMENDATION: recommended_type,
    Intent.INFLUENCER_OUTREACH: lambda _influencer: DeliverableType.INFLUENCER_OUTREACH,
}


def expected_type(intent: Intent, trigger: Record | None) -> DeliverableType | None:
    """The type a trigger fixes, or None for chat, where the user's request decides."""
    resolver = RESOLVERS.get(intent)
    if resolver is None or trigger is None:
        return None
    deliverable_type = resolver(trigger)
    if deliverable_type is None:
        raise ValidationError(
            f"{intent} has no deliverable for this record", {"ref_id": trigger.get("id")}
        )
    return deliverable_type
