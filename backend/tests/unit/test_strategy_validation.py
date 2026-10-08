"""Strategy post-validation: grounding, contract rules and normalisation."""

import pytest

from app.agents.common.errors import InvalidOutputError, UngroundedOutputError
from app.agents.strategy.output import Evidence
from app.agents.strategy.validation import (
    contract_problems,
    ensure_valid,
    normalise,
    unknown_ids,
)
from tests.strategy_samples import SECOND_SIGNAL, strategy_output
from tests.strategy_samples import niche_recommendation as recommendation
from tests.strategy_samples import recommendation as sample


def test_unknown_ids_are_the_cited_ids_not_retrieved() -> None:
    output = strategy_output(recommendation(1, "act_1"), recommendation(2, "act_invented"))
    assert unknown_ids(output, {"act_1", SECOND_SIGNAL}) == ["act_invented"]


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
        ensure_valid(output, {"act_1", SECOND_SIGNAL}, {"pricing"})


def test_normalise_renumbers_and_caps_lengths() -> None:
    long = recommendation(7, "act_1").model_copy(
        update={"title": "t" * 200, "insight": " " + "i" * 300, "audience": "a" * 100 + " "}
    )
    output = normalise(strategy_output(recommendation(4, "act_1"), long))
    assert [rec.ordinal for rec in output.recommendations] == [1, 2]
    capped = output.recommendations[1]
    assert (len(capped.title), len(capped.insight), len(capped.audience)) == (90, 240, 80)
    assert capped.insight.startswith("i")


def niche(rec_problems: list[str]) -> list[str]:
    return [p for p in rec_problems if "signal" in p or "competitor" in p or "needs an" in p]


def test_a_recommendation_needs_two_external_signals() -> None:
    single = sample(1, "act_1")
    with_company = single.model_copy(
        update={"evidence": [*single.evidence, Evidence(id="cmp_1", kind="company", note="Us")]}
    )
    for rec in (single, with_company):
        (problem,) = niche(contract_problems(strategy_output(rec), {"pricing"}))
        assert "at least 2 distinct signals" in problem
    assert niche(contract_problems(strategy_output(recommendation(1, "act_1")), {"pricing"})) == []


def test_activities_must_come_from_two_competitors() -> None:
    rec = sample(1, "act_1")
    two_moves = rec.model_copy(
        update={"evidence": [*rec.evidence, Evidence(id="act_2", kind="activity", note="Again")]}
    )
    output = strategy_output(two_moves)
    same = {"act_1": "cpt_brightlane", "act_2": "cpt_brightlane"}
    (problem,) = niche(contract_problems(output, {"pricing"}, same))
    assert "only one competitor" in problem
    rivals = {"act_1": "cpt_brightlane", "act_2": "cpt_kestrel"}
    assert niche(contract_problems(output, {"pricing"}, rivals)) == []


def test_insight_and_audience_are_required_except_for_monitor() -> None:
    blank = recommendation(1, "act_1").model_copy(update={"insight": " ", "audience": ""})
    monitor = sample(2, "act_1", kind="MONITOR", next_action=False)
    monitor = monitor.model_copy(update={"insight": "", "audience": ""})
    problems = niche(contract_problems(strategy_output(blank, monitor), {"pricing"}))
    assert [p.split(" needs")[0] for p in problems] == ["recommendation 1", "recommendation 1"]


def test_more_than_five_recommendations_is_a_problem() -> None:
    output = strategy_output(*(recommendation(i, "act_1") for i in range(1, 7)))
    assert contract_problems(output, {"pricing"})[0].startswith("return at most 5")
    assert contract_problems(strategy_output(*output.recommendations[:5]), {"pricing"}) == []
