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
from typing import TypeVar

from pydantic import BaseModel

from evals.calibration import agreement, calibration_line, sample
from evals.cases import CaseFileError, GoldenCase, check_fixture_ids, golden_path, parse_cases
from evals.fixture import EVALUATION_DIR, load_fixture
from evals.judge import JudgeBundle, JudgeScore, ScoreFileError, make_bundles, read_scores
from evals.report import build_report, to_markdown
from evals.runner import RunRecord, run_suite

REPORTS_DIR = EVALUATION_DIR / "reports"
RUBRICS_DIR = EVALUATION_DIR / "rubrics"


class RunMeta(BaseModel):
    suite: str
    fixture: str
    repeats: int
    started_at: datetime


def write_jsonl(path: Path, items: list[BaseModel]) -> None:
    path.write_text("".join(item.model_dump_json() + "\n" for item in items), encoding="utf-8")


ModelT = TypeVar("ModelT", bound=BaseModel)


def read_jsonl(path: Path, model: type[ModelT]) -> list[ModelT]:
    lines = path.read_text("utf-8").splitlines()
    return [model.model_validate_json(line) for line in lines if line.strip()]


def resolve_run_dir(value: str) -> Path:
    """Relative run directories are read from the repository root, where `run` prints them;
    `uv run --directory backend` would otherwise resolve them inside backend/."""
    path = Path(value)
    return path if path.is_absolute() else EVALUATION_DIR.parent / path


def write_report(run_dir: Path) -> bool:
    """Rebuild report.{json,md} from the run directory; True when baseline-ready."""
    meta = RunMeta.model_validate_json((run_dir / "meta.json").read_text("utf-8"))
    cases = read_jsonl(run_dir / "cases.jsonl", GoldenCase)
    records = read_jsonl(run_dir / "runs.jsonl", RunRecord)
    bundles = read_jsonl(run_dir / "bundles.jsonl", JudgeBundle)
    scores_path = run_dir / "scores.jsonl"
    scores = (
        read_scores(scores_path, meta.suite, {b.bundle_id for b in bundles})
        if scores_path.exists()
        else {}
    )
    report = build_report(meta.suite, cases, records, load_fixture(meta.fixture), scores)
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
        args.suite, cases, fixture, repeats=args.repeats, concurrency=args.concurrency
    )
    write_jsonl(run_dir / "runs.jsonl", list(records))
    write_jsonl(run_dir / "bundles.jsonl", list(make_bundles(args.suite, cases, records, fixture)))
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
    if not ready:
        sys.stderr.write("evals: not a baseline (judging incomplete or a threshold failed)\n")
        return 1
    suite = RunMeta.model_validate_json((run_dir / "meta.json").read_text("utf-8")).suite
    baseline = REPORTS_DIR / f"baseline_{suite}.json"
    baseline.write_text((run_dir / "report.json").read_text("utf-8"), encoding="utf-8")
    sys.stdout.write(f"evals: wrote {baseline.name}\n")
    return 0


def calibrate(args: argparse.Namespace) -> int:
    run_dir = resolve_run_dir(args.run_dir)
    meta = RunMeta.model_validate_json((run_dir / "meta.json").read_text("utf-8"))
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
    line = calibration_line(len(owner), agreement(owner, judge))
    rubric = RUBRICS_DIR / f"{meta.suite}.md"
    with rubric.open("a", encoding="utf-8") as file:
        file.write(line + "\n")
    sys.stdout.write(line + "\n")
    return 0 if "PASS" in line else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden-dataset eval harness")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run cases against the real agent")
    run_parser.add_argument("--suite", choices=["strategy"], required=True)
    run_parser.add_argument("--repeats", type=int, default=1)
    run_parser.add_argument("--cases", nargs="+", default=["*"], help="case ID globs")
    run_parser.add_argument("--concurrency", type=int, default=4)
    report_parser = commands.add_parser("report", help="merge judge scores and apply thresholds")
    report_parser.add_argument("run_dir")
    report_parser.add_argument("--baseline", action="store_true")
    calibrate_parser = commands.add_parser("calibrate", help="owner scoring for judge calibration")
    calibrate_parser.add_argument("run_dir")
    calibrate_parser.add_argument("action", choices=["sample", "compare"])
    args = parser.parse_args()
    commands_by_name = {
        "run": lambda a: asyncio.run(run(a)),
        "report": report,
        "calibrate": calibrate,
    }
    try:
        return commands_by_name[args.command](args)
    except (CaseFileError, ScoreFileError) as exc:
        sys.stderr.write(f"evals: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
