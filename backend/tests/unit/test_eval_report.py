"""Judge contract, report thresholds, baseline gate and calibration."""

import argparse
from pathlib import Path
from typing import Any

import pytest

from evals import cli
from evals.calibration import agreement, sample
from evals.cases import GoldenCase
from evals.fixture import load_fixture
from evals.judge import JudgeScore, ScoreFileError, make_bundles, read_scores
from evals.report import build_report
from evals.runner import RunRecord
from tests.strategy_samples import recommendation, strategy_output

FIXTURE = load_fixture("intelligence_v1")
DIMS = ("relevance", "grounding", "actionability", "marketing_soundness")


def case(case_id: str, category: str = "ST-TOPIC") -> GoldenCase:
    return GoldenCase.model_validate(
        {
            "id": case_id,
            "suite": "strategy",
            "category": category,
            "fixture": "intelligence_v1",
            "description": "report test",
            "input": {"message": "What should we post?"},
            "expect": {"status": ["OK"]},
        }
    )


def good_record(case_id: str, repeat: int = 1) -> RunRecord:
    run: dict[str, Any] = {
        "output": strategy_output(recommendation(1, "act_seed_001")).model_dump(mode="json"),
        "tool_calls": [{"tool": "get_company_context"}],
        "skills_loaded": ["pricing"],
        "usage": {"total_tokens": 1000},
        "events": [{"type": "run.completed", "data": {"duration_ms": 20_000}}],
    }
    return RunRecord(case_id=case_id, repeat=repeat, run=run, retrieved_ids=["act_seed_001"])


def score(bundle_id: str, value: int = 5) -> JudgeScore:
    return JudgeScore(bundle_id=bundle_id, scores=dict.fromkeys(DIMS, value), rationale="ok")


CASES = [case("ST-1"), case("SAFE-INJ-1", "SAFE-INJ")]
RECORDS = [good_record("ST-1"), good_record("SAFE-INJ-1")]


def test_missing_scores_block_the_baseline() -> None:
    report = build_report("strategy", CASES, RECORDS, FIXTURE, {})
    assert not report.judge_complete and not report.baseline_ready
    judge = {m.name: m for m in report.metrics if m.name.startswith("judge")}
    assert all(m.actual is None and not m.passed for m in judge.values())


def test_complete_passing_run_is_baseline_ready() -> None:
    scores = {s.bundle_id: s for s in (score("ST-1#1"), score("SAFE-INJ-1#1"))}
    report = build_report("strategy", CASES, RECORDS, FIXTURE, scores)
    assert report.judge_complete and report.baseline_ready, report.metrics


def test_low_judge_scores_or_a_failed_safe_case_fail_thresholds() -> None:
    low = {s.bundle_id: s for s in (score("ST-1#1", 3), score("SAFE-INJ-1#1", 3))}
    assert not build_report("strategy", CASES, RECORDS, FIXTURE, low).passed
    broken = [RECORDS[0], RunRecord(case_id="SAFE-INJ-1", repeat=1, run=None, retrieved_ids=[])]
    report = build_report("strategy", CASES, broken, FIXTURE, {})
    safe = next(m for m in report.metrics if m.name == "safe_categories")
    assert safe.actual == 0.0 and not safe.passed


def test_score_file_is_validated(tmp_path: Path) -> None:
    path = tmp_path / "scores.jsonl"
    ids = {"ST-1#1"}
    path.write_text(score("ST-1#1").model_dump_json() + "\n", encoding="utf-8")
    assert set(read_scores(path, "strategy", ids)) == ids
    for bad in (
        '{"bundle_id": "ST-9#1", "scores": {}, "rationale": "x"}',
        '{"bundle_id": "ST-1#1", "scores": {"relevance": 5}, "rationale": "x"}',
        score("ST-1#1").model_dump_json().replace('"relevance":5', '"relevance":7'),
    ):
        path.write_text(bad + "\n", encoding="utf-8")
        with pytest.raises(ScoreFileError):
            read_scores(path, "strategy", ids)


def test_calibration_agreement_and_balanced_sample() -> None:
    owner = {"a": score("a", 4)}
    assert agreement(owner, {"a": score("a", 5)}) == 1.0
    assert agreement(owner, {"a": score("a", 2)}) == 0.0
    cases = [case(f"T-{i}") for i in range(6)] + [case("S-1", "SAFE-INJ")]
    records = [good_record(c.id) for c in cases]
    chosen = sample(make_bundles("strategy", cases, records, FIXTURE), size=2)
    assert {b.case["category"] for b in chosen} == {"ST-TOPIC", "SAFE-INJ"}


def test_cli_refuses_a_baseline_without_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = tmp_path / "strategy_run"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(
        '{"suite": "strategy", "fixture": "intelligence_v1", "repeats": 1,'
        ' "started_at": "2026-09-30T00:00:00Z"}',
        encoding="utf-8",
    )
    cli.write_jsonl(run_dir / "cases.jsonl", list(CASES))
    cli.write_jsonl(run_dir / "runs.jsonl", list(RECORDS))
    cli.write_jsonl(
        run_dir / "bundles.jsonl", list(make_bundles("strategy", CASES, RECORDS, FIXTURE))
    )
    monkeypatch.setattr(cli, "REPORTS_DIR", tmp_path)
    args = argparse.Namespace(run_dir=str(run_dir), baseline=True)
    assert cli.report(args) == 1
    assert not (tmp_path / "baseline_strategy.json").exists()
    assert (run_dir / "report.md").exists()
