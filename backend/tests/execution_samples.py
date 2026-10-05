"""Small ExecutionOutput builders shared by the Execution tests."""

from app.agents.execution.output import (
    ActionProposal,
    ExecutionDeliverable,
    ExecutionOutput,
    QualityCheck,
)
from app.agents.execution.validation import IMAGES_FOR
from app.intelligence.models import ActionType, Channel, DeliverableType, ImageSuggestion


def deliverable(
    deliverable_type: DeliverableType = DeliverableType.LINKEDIN_POST,
    body: str = "We help B2B teams make the next decision easier.",
) -> ExecutionDeliverable:
    return ExecutionDeliverable(
        type=deliverable_type,
        channel=Channel.LINKEDIN,
        title="A clearer next decision",
        body_markdown=body,
        variants=[],
        word_count=0,
        author_persona=None,
        image_suggestions=[
            ImageSuggestion(
                placement="Post attachment",
                content="A sticky-note map of one buyer's next decision",
                style="Overhead photo, natural light",
            )
        ]
        * IMAGES_FOR[deliverable_type][0],
    )


def execution_output(
    item: ExecutionDeliverable | None = None,
    *,
    evidence_ids: tuple[str, ...] = ("act_1",),
    actions: tuple[ActionType, ...] = (ActionType.SCHEDULE_SOCIAL_POST,),
) -> ExecutionOutput:
    item = item if item is not None else deliverable()
    return ExecutionOutput(
        status="OK",
        message="Here is a LinkedIn post.",
        deliverable=item,
        quality_check=QualityCheck(
            brand_voice="PASS",
            originality="PASS",
            factual_grounding="PASS",
            channel_fit="PASS",
            notes=[],
        ),
        evidence_ids=list(evidence_ids),
        skills_used=["social"],
        assumptions=[],
        proposed_actions=[
            ActionProposal(action_type=action, summary="Schedule it", when=None)
            for action in actions
        ],
        clarification_options=[],
    )


def clarification() -> ExecutionOutput:
    return ExecutionOutput(
        status="NEEDS_CLARIFICATION",
        message="What should I write?",
        deliverable=None,
        quality_check=None,
        evidence_ids=[],
        skills_used=[],
        assumptions=[],
        proposed_actions=[],
        clarification_options=["A LinkedIn post", "A blog outline"],
    )
