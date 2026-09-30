"""Judge calibration (evaluation-spec §5.2): the owner scores a sample, the judge must agree.

Agreement is the share of (bundle, dimension) pairs where the judge is within ±1 of the
owner; a baseline needs at least 80% over 50 owner-scored runs (owner decision 2026-09-29).
"""

from collections import defaultdict
from datetime import date
from itertools import zip_longest

from evals.judge import JudgeBundle, JudgeScore

SAMPLE_SIZE = 50
MIN_AGREEMENT = 0.80


def sample(bundles: list[JudgeBundle], size: int = SAMPLE_SIZE) -> list[JudgeBundle]:
    """Deterministic, category-balanced sample: round-robin over categories."""
    by_category: dict[str, list[JudgeBundle]] = defaultdict(list)
    for bundle in sorted(bundles, key=lambda b: b.bundle_id):
        by_category[str(bundle.case["category"])].append(bundle)
    rounds = zip_longest(*(by_category[c] for c in sorted(by_category)))
    return [b for batch in rounds for b in batch if b is not None][:size]


def agreement(owner: dict[str, JudgeScore], judge: dict[str, JudgeScore]) -> float:
    pairs = [
        abs(score - judge[bundle].scores[dim]) <= 1
        for bundle, scored in owner.items()
        if bundle in judge
        for dim, score in scored.scores.items()
    ]
    return sum(pairs) / len(pairs) if pairs else 0.0


def calibration_line(owner_count: int, value: float) -> str:
    verdict = "PASS" if owner_count >= SAMPLE_SIZE and value >= MIN_AGREEMENT else "FAIL"
    return (
        f"- {date.today().isoformat()}: {owner_count} owner-scored runs, "
        f"agreement within ±1 = {value:.0%} ({verdict}, needs {MIN_AGREEMENT:.0%} "
        f"over {SAMPLE_SIZE})"
    )
