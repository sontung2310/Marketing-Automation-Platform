"""The Claude-judge file contract (evaluation-spec §5.2, decision 2026-09-29).

The harness writes one bundle per schema-valid run; Claude subagents (the `eval-judge`
team skill) score them against the rubric and write scores.jsonl; code validates it.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from evals.cases import GoldenCase
from evals.fixture import FixtureBundle
from evals.runner import RunRecord

DIMENSIONS: dict[str, tuple[str, ...]] = {
    "strategy": ("relevance", "grounding", "actionability", "marketing_soundness"),
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
    brand_voice: dict[str, object]


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    scores: dict[str, int]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def scores_are_one_to_five(self) -> "JudgeScore":
        if not all(1 <= score <= 5 for score in self.scores.values()):
            raise ValueError("scores must be integers from 1 to 5")
        return self


class ScoreFileError(ValueError):
    """A score file is malformed or does not match the bundles."""


def make_bundles(
    suite: str, cases: list[GoldenCase], records: list[RunRecord], fixture: FixtureBundle
) -> list[JudgeBundle]:
    by_id = {case.id: case for case in cases}
    brand_voice = fixture.companies[0].brand_voice.model_dump(mode="json")
    bundles = []
    for record in records:
        output = (record.run or {}).get("output")
        if not isinstance(output, dict):
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
                brand_voice=brand_voice,
            )
        )
    return bundles


def read_scores(path: Path, suite: str, bundle_ids: set[str]) -> dict[str, JudgeScore]:
    """Validated scores keyed by bundle; unknown bundles or wrong dimensions are errors."""
    scores: dict[str, JudgeScore] = {}
    expected = set(DIMENSIONS[suite])
    for number, line in enumerate(path.read_text("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            score = JudgeScore.model_validate(json.loads(line))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ScoreFileError(f"{path.name}:{number}: {exc}") from exc
        if score.bundle_id not in bundle_ids:
            raise ScoreFileError(f"{path.name}:{number}: unknown bundle {score.bundle_id}")
        if set(score.scores) != expected:
            raise ScoreFileError(f"{path.name}:{number}: dimensions must be {sorted(expected)}")
        scores[score.bundle_id] = score
    return scores
