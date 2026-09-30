"""Eval harness CLI (evaluation-spec §2).

    uv run --directory backend python -m evals.cli run --suite strategy --repeats 3
    uv run --directory backend python -m evals.cli report <run_dir> [--baseline]
    uv run --directory backend python -m evals.cli calibrate <run_dir> sample|compare

`run` calls the real agent (OpenAI) and writes runs, judge bundles and an unjudged report
into evaluation/reports/<suite>_<timestamp>/. Claude judges the bundles with the
`eval-judge` skill (scores.jsonl); `report` then merges scores and applies §6 thresholds.
"""

import argparse
import asyncio
import fnmatch
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from evals.calibration import CalibrationResult, calibration_line, sample
from evals.calibration import calibrate as calibrate_judge
from evals.cases import (
    CaseFileError,
    GoldenCase,
    Suite,
    check_fixture_ids,
    golden_path,
    parse_cases,
)
from evals.files import read_jsonl, write_jsonl
from evals.fixture import EVALUATION_DIR, load_fixture, shifted_to
from evals.judge import JudgeBundle, JudgeScore, ScoreFileError, make_bundles, read_scores
from evals.report import build_report, to_markdown
from evals.runner import RunRecord, run_suite

REPORTS_DIR = EVALUATION_DIR / "reports"
RUBRICS_DIR = EVALUATION_DIR / "rubrics"


class RunMeta(BaseModel):
    suite: Suite
    fixture: str
    repeats: int
    started_at: datetime


def read_meta(run_dir: Path) -> RunMeta:
    return RunMeta.model_validate_json((run_dir / "meta.json").read_text("utf-8"))


def resolve_run_dir(value: str) -> Path:
    """Relative run directories are read from the repository root, where `run` prints them;
    `uv run --directory backend` would otherwise resolve them inside backend/."""
    path = Path(value)
    return path if path.is_absolute() else EVALUATION_DIR.parent / path


BASELINE_REPEATS = 3  # evaluation-spec §5.3


def calibration_path(suite: str) -> Path:
    return RUBRICS_DIR / f"{suite}.calibration.json"


def baseline_problems(run_dir: Path, report_ready: bool) -> list[str]:
    """Why this run cannot become the suite's baseline (empty when it can)."""
    meta = read_meta(run_dir)
    problems = [] if report_ready else ["judging is incomplete or a threshold failed"]
    if meta.repeats != BASELINE_REPEATS:
        problems.append(f"it ran {meta.repeats} repeat(s), a baseline needs {BASELINE_REPEATS}")
    ran = {c.id for c in read_jsonl(run_dir / "cases.jsonl", GoldenCase, CaseFileError)}
    golden = {c.id for c in parse_cases(golden_path(meta.suite))}
    if ran != golden:
        problems.append(f"it ran {len(ran)} of the {len(golden)} golden cases")
    calibration = calibration_path(meta.suite)
    if (
        not calibration.is_file()
        or not CalibrationResult.model_validate_json(calibration.read_text("utf-8")).passed
    ):
        problems.append("the judge has no passing calibration (`calibrate ... compare`)")
    return problems


def write_report(run_dir: Path) -> bool:
    """Rebuild report.{json,md} from the run directory; True when the report passes."""
    meta = read_meta(run_dir)
    cases = read_jsonl(run_dir / "cases.jsonl", GoldenCase, CaseFileError)
    records = read_jsonl(run_dir / "runs.jsonl", RunRecord)
    bundles = read_jsonl(run_dir / "bundles.jsonl", JudgeBundle)
    scores_path = run_dir / "scores.jsonl"
    scores = (
        read_scores(scores_path, meta.suite, {b.bundle_id for b in bundles})
        if scores_path.exists()
        else {}
    )
    fixture = shifted_to(load_fixture(meta.fixture), meta.started_at)
    report = build_report(meta.suite, cases, records, fixture, scores, meta.repeats)
    (run_dir / "report.json").write_text(report.model_dump_json(indent=1), encoding="utf-8")
    (run_dir / "report.md").write_text(to_markdown(report), encoding="utf-8")
    return report.baseline_ready


async def run(args: argparse.Namespace) -> int:
    all_cases = parse_cases(golden_path(args.suite))
    cases = [c for c in all_cases if any(fnmatch.fnmatch(c.id, p) for p in args.cases)]
    if not cases:
        sys.stderr.write(f"evals: no {args.suite} cases match {args.cases}\n")
        return 1
    fixture = load_fixture(cases[0].fixture)
    check_fixture_ids(cases, fixture)
    started = datetime.now(UTC)
    run_dir = REPORTS_DIR / f"{args.suite}_{started:%Y%m%dT%H%M%SZ}"
    run_dir.mkdir(parents=True)
    meta = RunMeta(
        suite=args.suite, fixture=fixture.version, repeats=args.repeats, started_at=started
    )
    (run_dir / "meta.json").write_text(meta.model_dump_json(indent=1), encoding="utf-8")
    write_jsonl(run_dir / "cases.jsonl", list(cases))
    records = await run_suite(
        args.suite, cases, fixture, now=started, repeats=args.repeats, concurrency=args.concurrency
    )
    write_jsonl(run_dir / "runs.jsonl", list(records))
    shifted = shifted_to(fixture, started)
    write_jsonl(run_dir / "bundles.jsonl", list(make_bundles(args.suite, cases, records, shifted)))
    write_report(run_dir)
    shown = run_dir.relative_to(EVALUATION_DIR.parent)
    sys.stdout.write(f"evals: {len(records)} runs in {shown} (judge with the eval-judge skill)\n")
    return 0


def report(args: argparse.Namespace) -> int:
    run_dir = resolve_run_dir(args.run_dir)
    ready = write_report(run_dir)
    sys.stdout.write((run_dir / "report.md").read_text("utf-8"))
    if not args.baseline:
        return 0
    if problems := baseline_problems(run_dir, ready):
        sys.stderr.write("evals: not a baseline: " + "; ".join(problems) + "\n")
        return 1
    baseline = REPORTS_DIR / f"baseline_{read_meta(run_dir).suite}.json"
    baseline.write_text((run_dir / "report.json").read_text("utf-8"), encoding="utf-8")
    sys.stdout.write(f"evals: wrote {baseline.name}\n")
    return 0


def calibrate(args: argparse.Namespace) -> int:
    run_dir = resolve_run_dir(args.run_dir)
    meta = read_meta(run_dir)
    bundles = read_jsonl(run_dir / "bundles.jsonl", JudgeBundle)
    ids = {b.bundle_id for b in bundles}
    if args.action == "sample":
        chosen = sample(bundles)
        template = [
            JudgeScore(
                bundle_id=b.bundle_id, scores=dict.fromkeys(b.dimensions, 3), rationale="TODO"
            )
            for b in chosen
        ]
        write_jsonl(run_dir / "calibration_bundles.jsonl", list(chosen))
        write_jsonl(run_dir / "human_scores.jsonl", list(template))
        sys.stdout.write(
            f"evals: {len(chosen)} bundles in calibration_bundles.jsonl; replace the placeholder "
            "3s and rationales in human_scores.jsonl, then run `calibrate <dir> compare`\n"
        )
        return 0
    owner = read_scores(run_dir / "human_scores.jsonl", meta.suite, ids)
    if any(score.rationale == "TODO" for score in owner.values()):
        sys.stderr.write("evals: human_scores.jsonl still has TODO placeholders\n")
        return 1
    judge = read_scores(run_dir / "scores.jsonl", meta.suite, ids)
    result = calibrate_judge(meta.suite, owner, judge)
    line = calibration_line(result)
    with (RUBRICS_DIR / f"{meta.suite}.md").open("a", encoding="utf-8") as file:
        file.write(line + "\n")
    calibration_path(meta.suite).write_text(result.model_dump_json(indent=1), encoding="utf-8")
    sys.stdout.write(line + "\n")
    return 0 if result.passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-dataset eval harness")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run cases against the real agent")
    run_parser.set_defaults(func=lambda a: asyncio.run(run(a)))
    run_parser.add_argument("--suite", choices=["strategy"], required=True)
    run_parser.add_argument("--repeats", type=int, default=1)
    run_parser.add_argument("--cases", nargs="+", default=["*"], help="case ID globs")
    run_parser.add_argument("--concurrency", type=int, default=4)
    report_parser = commands.add_parser("report", help="merge judge scores and apply thresholds")
    report_parser.set_defaults(func=report)
    report_parser.add_argument("run_dir")
    report_parser.add_argument("--baseline", action="store_true")
    calibrate_parser = commands.add_parser("calibrate", help="owner scoring for judge calibration")
    calibrate_parser.set_defaults(func=calibrate)
    calibrate_parser.add_argument("run_dir")
    calibrate_parser.add_argument("action", choices=["sample", "compare"])
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except (CaseFileError, ScoreFileError) as exc:
        sys.stderr.write(f"evals: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
