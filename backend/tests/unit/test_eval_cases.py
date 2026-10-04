"""Golden-case loading: schema, duplicates and fixture-ID validation happen before any run."""

import json
from pathlib import Path

import pytest

from evals.cases import CaseFileError, check_fixture_ids, parse_cases
from evals.fixture import load_fixture
from tests.strategy_samples import golden_case_data


def case(case_id: str, ref_id: str = "act_seed_026") -> dict[str, object]:
    trigger = {"kind": "FEED_ACTION", "ref_id": ref_id, "action": "RESPONSE_PLAN"}
    return golden_case_data(
        id=case_id,
        input={"trigger": trigger},
        expect={"status": ["OK"], "evidence_required_all": [ref_id]},
    )


def write(tmp_path: Path, *cases: dict[str, object]) -> Path:
    path = tmp_path / "strategy.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in cases) + "\n", encoding="utf-8")
    return path


def test_valid_cases_load_and_match_the_fixture(tmp_path: Path) -> None:
    cases = parse_cases(write(tmp_path, case("ST-1"), case("ST-2", "act_fx_inject_02")))
    check_fixture_ids(cases, load_fixture("intelligence_v2"))
    assert [c.id for c in cases] == ["ST-1", "ST-2"]


def test_missing_fixture_id_is_named_before_any_run(tmp_path: Path) -> None:
    cases = parse_cases(write(tmp_path, case("ST-GONE", "act_does_not_exist")))
    with pytest.raises(CaseFileError, match=r"ST-GONE.*act_does_not_exist"):
        check_fixture_ids(cases, load_fixture("intelligence_v2"))
    expect = {"status": ["OK"], "retrieved_any": ["act_typo"]}
    retrieved = golden_case_data(id="ST-TYPO", input={"message": "Hi"}, expect=expect)
    with pytest.raises(CaseFileError, match=r"ST-TYPO.*act_typo"):
        check_fixture_ids(parse_cases(write(tmp_path, retrieved)), load_fixture("intelligence_v2"))


def test_duplicate_ids_and_bad_lines_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CaseFileError, match="duplicate"):
        parse_cases(write(tmp_path, case("ST-1"), case("ST-1")))
    bad = case("ST-BAD") | {"unexpected": True}
    with pytest.raises(CaseFileError, match=r"strategy\.jsonl:1"):
        parse_cases(write(tmp_path, bad))


def test_ids_inside_session_history_must_exist(tmp_path: Path) -> None:
    history = [{"recommendations": [{"evidence": [{"id": "act_typo_404"}]}]}]
    line = case("ST-MULTI") | {"input": {"message": "Drop #1", "session_history": history}}
    cases = parse_cases(write(tmp_path, line))
    with pytest.raises(CaseFileError, match="act_typo_404"):
        check_fixture_ids(cases, load_fixture("intelligence_v2"))
