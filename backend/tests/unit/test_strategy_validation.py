"""Strategy post-validation: grounding, contract rules and normalisation."""

import pytest

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.strategy.validation import (
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
    problems = contract_problems(strategy_output(no_action, monitor, no_evidence), {"pricing"})
    assert problems == [
        "recommendation 1 (COMPETITIVE_RESPONSE) needs a next_action with a brief",
        "recommendation 3 cites no evidence",
    ]


def test_contract_rejects_empty_text_wrong_prefix_and_unloaded_skills() -> None:
    blank = recommendation(1, "act_1").model_copy(update={"rationale": "  "})
    wrong_kind = recommendation(2, "trd_1")  # cited as an activity
    problems = contract_problems(strategy_output(blank, wrong_kind), set())
    assert problems == [
        "recommendation 1 needs a title and a rationale",
        "recommendation 1 lists skills you did not load: pricing",
        "recommendation 2: trd_1 is not a activity ID",
        "recommendation 2 lists skills you did not load: pricing",
    ]


def test_insufficient_data_carries_no_recommendations() -> None:
    output = strategy_output(recommendation(1, "act_1")).model_copy(
        update={"status": "INSUFFICIENT_DATA"}
    )
    assert contract_problems(output, {"pricing"}) == [
        "an INSUFFICIENT_DATA answer must have no recommendations"
    ]
    assert contract_problems(output.model_copy(update={"recommendations": []}), set()) == []


def test_ensure_valid_raises_the_matching_error() -> None:
    with pytest.raises(UngroundedOutputError):
        ensure_valid(strategy_output(recommendation(1, "act_x")), set(), {"pricing"})
    with pytest.raises(InvalidOutputError):
        output = strategy_output(recommendation(1, "act_1", next_action=False))
        ensure_valid(output, {"act_1"}, {"pricing"})


def test_normalise_renumbers_and_caps_lengths() -> None:
    long = recommendation(7, "act_1").model_copy(update={"title": "t" * 200})
    output = normalise(strategy_output(recommendation(4, "act_1"), long))
    assert [rec.ordinal for rec in output.recommendations] == [1, 2]
    assert len(output.recommendations[1].title) == 90
