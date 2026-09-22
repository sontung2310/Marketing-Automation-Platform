"""Validate or seed the platform-owned Intelligence DB.

Run from the repository root with:
    uv run --directory backend python scripts/seed_db.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.core import db
from app.pipelines.seed.loader import SeedValidationError, load_seed_bundle, validate_seed_bundle
from app.pipelines.seed.writer import seed_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=None,
        help="directory containing the six seed JSON files (defaults to app/pipelines/seed)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and report planned counts without touching MongoDB",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    try:
        bundle = load_seed_bundle(args.seed_dir) if args.seed_dir else load_seed_bundle()
        coverage = validate_seed_bundle(bundle)
        if args.dry_run:
            _write_json({"mode": "dry-run", "coverage": coverage.__dict__})
            return 0
        summary = await seed_database(db.get_database(), bundle)
        _write_json({"mode": "write", **summary.as_dict()})
        return 0
    except (SeedValidationError, ValueError) as exc:
        sys.stderr.write(f"seed validation failed: {exc}\n")
        return 2
    finally:
        if db.get_client.cache_info().currsize:
            await db.get_client().close()
            db.get_client.cache_clear()


def _write_json(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, default=str, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
