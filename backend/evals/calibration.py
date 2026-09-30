"""Judge calibration (evaluation-spec §5.2): the owner scores a sample, the judge must agree.

Agreement is the share of (bundle, dimension) pairs where the judge is within ±1 of the
owner; a baseline needs at least 80% over 50 owner-scored runs (owner decision 2026-09-29).
"""

from collections import defaultdict
from datetime import date
from itertools import zip_longest

from pydantic import BaseModel

from evals.judge import JudgeBundle, JudgeScore
from evals.report import share

SAMPLE_SIZE = 50
MIN_AGREEMENT = 0.80


class CalibrationResult(BaseModel):
    """The latest calibration of a suite's judge; the baseline gate reads it."""

    suite: str
    on: date
    compared: int  # owner-scored bundles that the judge also scored
    agreement: float
    passed: bool


def sample(bundles: list[JudgeBundle], size: int = SAMPLE_SIZE) -> list[JudgeBundle]:
    """Deterministic, category-balanced sample: round-robin over categories."""
    by_category: dict[str, list[JudgeBundle]] = defaultdict(list)
    for bundle in sorted(bundles, key=lambda b: b.bundle_id):
        by_category[str(bundle.case["category"])].append(bundle)
    rounds = zip_longest(*(by_category[c] for c in sorted(by_category)))
    return [b for batch in rounds for b in batch if b is not None][:size]


def agreement(owner: dict[str, JudgeScore], judge: dict[str, JudgeScore]) -> float:
    return share(
        [
            abs(score - judge[bundle].scores[dim]) <= 1
            for bundle, scored in owner.items()
            if bundle in judge
            for dim, score in scored.scores.items()
        ]
    )


def calibrate(
    suite: str, owner: dict[str, JudgeScore], judge: dict[str, JudgeScore]
) -> CalibrationResult:
    """Only bundles scored by both count, so a judge file missing samples cannot pass."""
    compared = {bundle: score for bundle, score in owner.items() if bundle in judge}
    value = agreement(compared, judge)
    return CalibrationResult(
        suite=suite,
        on=date.today(),
        compared=len(compared),
        agreement=value,
        passed=len(compared) >= SAMPLE_SIZE and value >= MIN_AGREEMENT,
    )


def calibration_line(result: CalibrationResult) -> str:
    verdict = "PASS" if result.passed else "FAIL"
    return (
        f"- {result.on.isoformat()}: {result.compared} runs scored by both the owner and the "
        f"judge, agreement within ±1 = {result.agreement:.0%} ({verdict}, needs "
        f"{MIN_AGREEMENT:.0%} over {SAMPLE_SIZE})"
    )
