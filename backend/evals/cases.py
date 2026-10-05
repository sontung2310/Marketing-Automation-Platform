"""Golden cases (evaluation-spec §4): schema, loading and fixture-ID validation."""

import re
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.agents.common.mcp import collect_ids
from app.orchestration.routing import Trigger
from evals.files import read_jsonl
from evals.fixture import EVALUATION_DIR, FixtureBundle

GOLDEN_DIR = EVALUATION_DIR / "golden"
Suite = Literal["strategy", "execution"]  # the router suite arrives with Step 6
# A trigger ref_id "history:N" means recommendation N of the seeded session history (5-C).
HISTORY_REF = re.compile(r"^history:(\d+)$")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseInput(Strict):
    message: str | None = None
    agent_hint: Literal["AUTO", "STRATEGY", "EXECUTION"] = "AUTO"
    trigger: Trigger | None = None
    session_history: list[dict[str, object]] = []  # prior run outputs, oldest first


class ExpectedRoute(Strict):
    agent: Literal["STRATEGY", "EXECUTION", "NONE"]
    intent: str


class RecommendationBounds(Strict):
    min: int | None = None
    max: int | None = None
    kinds_required: list[str] = []


class DeliverableExpect(Strict):
    type: str | None = None
    channel: str | None = None
    max_chars: int | None = None
    min_words: int | None = None
    max_words: int | None = None
    first_person: bool = False  # CEO posts speak as the spokesperson
    author_persona_includes: str | None = None
    images_min: int | None = None  # image_suggestions bounds (design D11)
    images_max: int | None = None


class Expect(Strict):
    route: ExpectedRoute | None = None
    status: list[str]
    tools_required: list[str] = []
    tools_forbidden: list[str] = []
    evidence_required_all: list[str] = []
    evidence_required_any: list[str] = []
    evidence_forbidden: list[str] = []
    retrieved_any: list[str] = []  # the run fetched one of these (answers with nothing to cite)
    skills_any: list[str] = []
    recommendations: RecommendationBounds | None = None
    must_include_any: list[str] = []
    must_not_include: list[str] = []
    data_gaps_any: list[str] = []  # a data_gaps entry mentions one of these (e.g. recency)
    channels_only: list[str] = []  # every recommendation targets one of these channels
    each_cites_prefix: list[str] = []  # every recommendation cites an ID with one of these
    implications_min: int | None = None
    implications_max: int | None = None
    deliverable: DeliverableExpect | None = None  # execution only
    proposed_actions_any: list[str] = []  # execution: one of these action types is proposed
    max_tool_calls: int = 12


class GoldenCase(Strict):
    id: str
    suite: Suite
    category: str
    fixture: str
    description: str
    input: CaseInput
    expect: Expect
    rubric_focus: list[str] = []
    reference_notes: str = ""
    tags: list[str] = []
    source: str = "authored"

    def referenced_ids(self) -> set[str]:
        ids = set(self.expect.evidence_required_all + self.expect.evidence_required_any)
        ids |= set(self.expect.evidence_forbidden) | set(self.expect.retrieved_any)
        if self.input.trigger is not None and not HISTORY_REF.match(self.input.trigger.ref_id):
            ids.add(self.input.trigger.ref_id)
        # Follow-ups may re-cite what the history cited, so those IDs must exist too.
        return ids | collect_ids(self.input.session_history)


class CaseFileError(ValueError):
    """The golden file is malformed or references records its fixture does not hold."""


def golden_path(suite: Suite) -> Path:
    return GOLDEN_DIR / f"{suite}.jsonl"


def parse_cases(path: Path) -> list[GoldenCase]:
    cases = read_jsonl(path, GoldenCase, CaseFileError)
    duplicates = sorted(i for i, n in Counter(c.id for c in cases).items() if n > 1)
    if duplicates:
        raise CaseFileError(f"{path.name}: duplicate case IDs {duplicates}")
    return cases


def check_fixture_ids(cases: list[GoldenCase], fixture: FixtureBundle) -> None:
    """Fail before any agent runs if a case points at a record its fixture lacks."""
    known = fixture.ids()
    for case in cases:
        if case.fixture != fixture.version:
            raise CaseFileError(f"{case.id}: uses fixture {case.fixture}, not {fixture.version}")
        if missing := sorted(case.referenced_ids() - known):
            raise CaseFileError(f"{case.id}: IDs not in {fixture.version}: {missing}")
