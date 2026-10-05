"""Judge contract, report thresholds, baseline gate and calibration."""

import argparse
from pathlib import Path

import pytest

from evals import cli
from evals.calibration import agreement, sample
from evals.calibration import calibrate as calibrate_judge
from evals.cases import GoldenCase
from evals.files import write_jsonl
from evals.fixture import EVALUATION_DIR, load_fixture
from evals.judge import JudgeScore, ScoreFileError, make_bundles, read_scores
from evals.report import build_report
from evals.runner import RunRecord
from tests.strategy_samples import golden_case, sample_run

FIXTURE = load_fixture("intelligence_v2")
DIMS = ("relevance", "grounding", "actionability", "marketing_soundness")


def case(case_id: str, category: str = "ST-TOPIC") -> GoldenCase:
    return golden_case(id=case_id, category=category)


def good_record(case_id: str, repeat: int = 1) -> RunRecord:
    run = sample_run()
    return RunRecord(case_id=case_id, repeat=repeat, run=run, retrieved_ids=["act_seed_001"])


def score(bundle_id: str, value: int = 5) -> JudgeScore:
    return JudgeScore(bundle_id=bundle_id, scores=dict.fromkeys(DIMS, value), rationale="ok")


CASES = [case("ST-1"), case("SAFE-INJ-1", "SAFE-INJ")]
RECORDS = [good_record("ST-1"), good_record("SAFE-INJ-1")]


def test_missing_scores_block_the_baseline() -> None:
    report = build_report("strategy", CASES, RECORDS, FIXTURE, {}, 1)
    assert not report.judge_complete and not report.baseline_ready
    judge = {m.name: m for m in report.metrics if m.name.startswith("judge")}
    assert all(m.actual is None and not m.passed for m in judge.values())


def test_complete_passing_run_is_baseline_ready() -> None:
    scores = {s.bundle_id: s for s in (score("ST-1#1"), score("SAFE-INJ-1#1"))}
    report = build_report("strategy", CASES, RECORDS, FIXTURE, scores, 1)
    assert report.judge_complete and report.baseline_ready, report.metrics


def test_low_judge_scores_or_a_failed_safe_case_fail_thresholds() -> None:
    low = {s.bundle_id: s for s in (score("ST-1#1", 3), score("SAFE-INJ-1#1", 3))}
    assert not build_report("strategy", CASES, RECORDS, FIXTURE, low, 1).passed
    broken = [RECORDS[0], RunRecord(case_id="SAFE-INJ-1", repeat=1, run=None, retrieved_ids=[])]
    report = build_report("strategy", CASES, broken, FIXTURE, {}, 1)
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


def make_run_dir(tmp_path: Path, *, scored: bool) -> Path:
    run_dir = tmp_path / "strategy_run"
    run_dir.mkdir()
    (run_dir / "meta.json").write_text(
        '{"suite": "strategy", "fixture": "intelligence_v2", "repeats": 1,'
        ' "started_at": "2026-09-22T00:00:00Z"}',
        encoding="utf-8",
    )
    write_jsonl(run_dir / "cases.jsonl", list(CASES))
    write_jsonl(run_dir / "runs.jsonl", list(RECORDS))
    write_jsonl(run_dir / "bundles.jsonl", list(make_bundles("strategy", CASES, RECORDS, FIXTURE)))
    if scored:
        write_jsonl(run_dir / "scores.jsonl", [score("ST-1#1"), score("SAFE-INJ-1#1")])
    return run_dir


def test_cli_refuses_a_baseline_without_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = make_run_dir(tmp_path, scored=False)
    monkeypatch.setattr(cli, "REPORTS_DIR", tmp_path)
    assert cli.report(argparse.Namespace(run_dir=str(run_dir), baseline=True)) == 1
    assert not (tmp_path / "baseline_strategy.json").exists()
    assert (run_dir / "report.md").exists()


def test_a_passing_partial_run_is_not_a_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir = make_run_dir(tmp_path, scored=True)
    monkeypatch.setattr(cli, "RUBRICS_DIR", tmp_path)
    monkeypatch.setattr(cli, "BASELINE_REPEATS", 3)  # the production setting
    assert cli.write_report(run_dir)  # every threshold passes on these two cases...
    problems = cli.baseline_problems(run_dir, report_ready=True)
    assert any("repeat" in p for p in problems)  # ...but 1 repeat, not 3
    assert any("golden cases" in p for p in problems)  # a subset of the golden set
    assert any("calibration" in p for p in problems)  # and an uncalibrated judge


def test_relative_run_dirs_resolve_from_the_repository_root() -> None:
    resolved = cli.resolve_run_dir("evaluation/reports/strategy_x")
    assert resolved == EVALUATION_DIR / "reports" / "strategy_x"
    assert cli.resolve_run_dir("/tmp/run") == Path("/tmp/run")


def test_a_case_missing_repeats_fails() -> None:
    scores = {s.bundle_id: s for s in (score("ST-1#1"), score("SAFE-INJ-1#1"))}
    report = build_report("strategy", CASES, RECORDS, FIXTURE, scores, repeats=3)
    assert not any(c.passed_all for c in report.cases)
    assert not report.passed


def test_an_outage_is_not_a_grounding_failure() -> None:
    outage = sample_run(status="FAILED", output=None, error={"code": "UPSTREAM_UNAVAILABLE"})
    ungrounded = sample_run(status="FAILED", output=None, error={"code": "UNGROUNDED_OUTPUT"})
    for run, expected in ((outage, 1.0), (ungrounded, 0.5)):
        records = [RECORDS[0], RunRecord(case_id="SAFE-INJ-1", repeat=1, run=run, retrieved_ids=[])]
        report = build_report("strategy", CASES, records, FIXTURE, {}, 1)
        grounded = next(m for m in report.metrics if m.name == "evidence_grounded_runs")
        assert grounded.actual == expected
    failing = next(c for c in report.cases if c.case_id == "SAFE-INJ-1")
    assert failing.errors == ["UNGROUNDED_OUTPUT"]


def test_one_weak_dimension_is_tolerated_but_not_below_three_and_a_half() -> None:
    def scored(weak: int) -> dict[str, JudgeScore]:
        values = {"relevance": 5, "grounding": 5, "actionability": weak, "marketing_soundness": 5}
        return {
            b: JudgeScore(bundle_id=b, scores=values, rationale="r")
            for b in ("ST-1#1", "SAFE-INJ-1#1")
        }

    assert build_report("strategy", CASES, RECORDS, FIXTURE, scored(4), 1).passed
    assert not build_report("strategy", CASES, RECORDS, FIXTURE, scored(3), 1).passed


def test_calibration_counts_only_bundles_scored_by_both() -> None:
    owner = {f"b{i}": score(f"b{i}", 4) for i in range(50)}
    judge = {f"b{i}": score(f"b{i}", 4) for i in range(10)}
    result = calibrate_judge("strategy", owner, judge)
    assert (result.compared, result.agreement, result.passed) == (10, 1.0, False)
    everything = {b: score(b, 5) for b in owner}
    assert calibrate_judge("strategy", owner, everything).passed


def test_the_per_category_bar_needs_three_repeats() -> None:
    def names(repeats: int) -> set[str]:
        records = [good_record(c.id, r) for c in CASES for r in range(1, repeats + 1)]
        report = build_report("strategy", CASES, records, FIXTURE, {}, repeats)
        return {m.name for m in report.metrics}

    assert "pass_all_per_category" not in names(1)
    assert "pass_all_per_category" in names(3)
