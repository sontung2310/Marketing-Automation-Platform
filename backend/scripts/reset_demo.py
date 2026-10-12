"""Reset the demo to a clean state: wipe session/run history, then re-seed.

Destructive: deletes every session, run, recommendation, deliverable, action
and simulated activity for the default company in the configured database
(MONGODB_DATABASE / .env). Requires --yes so it is never run by accident
against the wrong database.

Run from the repository root with:
    uv run --directory backend python scripts/reset_demo.py --yes
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.core import db
from app.core.config import get_settings
from app.pipelines.seed.loader import SeedValidationError, load_seed_bundle, validate_seed_bundle
from app.pipelines.seed.reset import reset_demo_state
from app.pipelines.seed.writer import seed_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm the wipe; without it, nothing is deleted or written",
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=None,
        help="directory containing the six seed JSON files (defaults to app/pipelines/seed)",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    settings = get_settings()
    company_id = settings.default_company_id
    target = {"database": settings.mongodb_database, "company_id": company_id}
    if not args.yes:
        _write_json(
            {
                "status": "error",
                "error": {
                    "code": "CONFIRMATION_REQUIRED",
                    "message": "Re-run with --yes to wipe and re-seed this database.",
                },
                "would_wipe": target,
            }
        )
        return 2
    try:
        bundle = load_seed_bundle(args.seed_dir) if args.seed_dir else load_seed_bundle()
        validate_seed_bundle(bundle)
        database = db.get_database()
        reset_counts = await reset_demo_state(database, company_id)
        seed_summary = await seed_database(database, bundle)
        _write_json(
            {
                "status": "ok",
                "wiped": target,
                "reset": asdict(reset_counts),
                "seed": seed_summary.as_dict(),
            }
        )
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
