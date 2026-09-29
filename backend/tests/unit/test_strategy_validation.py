"""Strategy post-validation: grounding, contract rules and normalisation."""

import pytest

from app.agents.strategy.validation import (
    InvalidOutputError,
    UngroundedOutputError,
    contract_problems,
    ensure_valid,
    normalise,
    unknown_ids,
)
from tests.strategy_samples import recommendation, strategy_output


def test_unknown_ids_are_the_cited_ids_not_retrieved() -> None:
    output = strategy_output(recommendation(1, "act_1"), recommendation(2, "act_invented"))
    assert unknown_ids(output, {"act_1", "cmp_marketing_eye"}) == ["act_invented"]


def test_contract_needs_evidence_and_next_action_except_monitor() -> None:
    no_action = recommendation(1, "act_1", next_action=False)
    monitor = recommendation(2, "act_1", kind="MONITOR", next_action=False)
    no_evidence = recommendation(3, "act_1").model_copy(update={"evidence": []})
    problems = contract_problems(strategy_output(no_action, monitor, no_evidence))
    assert problems == [
        "recommendation 1 (COMPETITIVE_RESPONSE) has no next_action",
        "recommendation 3 cites no evidence",
    ]


def test_ensure_valid_raises_the_matching_error() -> None:
    with pytest.raises(UngroundedOutputError):
        ensure_valid(strategy_output(recommendation(1, "act_x")), set())
    with pytest.raises(InvalidOutputError):
        ensure_valid(strategy_output(recommendation(1, "act_1", next_action=False)), {"act_1"})


def test_normalise_renumbers_and_caps_lengths() -> None:
    long = recommendation(7, "act_1").model_copy(update={"title": "t" * 200})
    output = normalise(strategy_output(recommendation(4, "act_1"), long))
    assert [rec.ordinal for rec in output.recommendations] == [1, 2]
    assert len(output.recommendations[1].title) == 90
