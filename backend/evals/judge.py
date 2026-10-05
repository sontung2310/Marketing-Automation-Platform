"""The Claude-judge file contract (evaluation-spec §5.2, decision 2026-09-29).

The harness writes one bundle per schema-valid run; Claude subagents (the `eval-judge`
team skill) score them against the rubric and write scores.jsonl; code validates it.
"""

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from evals.cases import GoldenCase
from evals.files import read_jsonl
from evals.fixture import FixtureBundle
from evals.runner import RunRecord

DIMENSIONS: dict[str, tuple[str, ...]] = {
    "strategy": ("relevance", "grounding", "actionability", "marketing_soundness"),
    # Owner decision 2026-10-05: four dimensions; grounding is checked in code.
    "execution": ("relevance", "marketing_quality", "brand_voice", "originality"),
}


def bundle_id(record: RunRecord) -> str:
    return f"{record.case_id}#{record.repeat}"


class JudgeBundle(BaseModel):
    bundle_id: str
    suite: str
    dimensions: list[str]
    case: dict[str, object]  # id, category, description, input, reference_notes, rubric_focus
    output: dict[str, object]
    evidence: list[dict[str, object]]  # the records the agent's tools returned
    tool_calls: list[dict[str, object]] = []  # what it searched, so absence claims can be judged
    brand_voice: dict[str, object]
    spokesperson: dict[str, object] | None = None  # whose voice a CEO post must use


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    scores: dict[str, Annotated[StrictInt, Field(ge=1, le=5)]]
    rationale: str = Field(min_length=1)


class ScoreFileError(ValueError):
    """A score file is malformed or does not match the bundles."""


def make_bundles(
    suite: str, cases: list[GoldenCase], records: list[RunRecord], fixture: FixtureBundle
) -> list[JudgeBundle]:
    by_id = {case.id: case for case in cases}
    brand_voice = fixture.companies[0].brand_voice.model_dump(mode="json")
    spokesperson = fixture.companies[0].spokesperson.model_dump(mode="json")
    bundles = []
    for record in records:
        output = record.run.output if record.run else None
        if output is None:
            continue  # the judge runs only on schema-valid output
        case = by_id[record.case_id]
        evidence = [r for i in record.retrieved_ids if (r := fixture.record(i)) is not None]
        bundles.append(
            JudgeBundle(
                bundle_id=bundle_id(record),
                suite=suite,
                dimensions=list(DIMENSIONS[suite]),
                case=case.model_dump(
                    mode="json",
                    include={
                        "id",
                        "category",
                        "description",
                        "input",
                        "reference_notes",
                        "rubric_focus",
                    },
                ),
                output=output,
                evidence=evidence,
                tool_calls=record.run.tool_calls if record.run else [],
                brand_voice=brand_voice,
                spokesperson=spokesperson if suite == "execution" else None,
            )
        )
    return bundles


def read_scores(path: Path, suite: str, bundle_ids: set[str]) -> dict[str, JudgeScore]:
    """Validated scores keyed by bundle; unknown bundles or wrong dimensions are errors."""
    scores: dict[str, JudgeScore] = {}
    expected = set(DIMENSIONS[suite])
    for score in read_jsonl(path, JudgeScore, ScoreFileError):
        if score.bundle_id not in bundle_ids:
            raise ScoreFileError(f"{path.name}: unknown bundle {score.bundle_id}")
        if score.bundle_id in scores:
            raise ScoreFileError(f"{path.name}: {score.bundle_id} is scored twice")
        if set(score.scores) != expected:
            raise ScoreFileError(
                f"{path.name}: {score.bundle_id} dimensions must be {sorted(expected)}"
            )
        scores[score.bundle_id] = score
    return scores
