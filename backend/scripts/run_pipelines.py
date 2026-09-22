"""Run the intelligence pipelines.

Run from the repository root with:
    uv run --directory backend python scripts/run_pipelines.py [--only NAME]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from app.core import db
from app.core.config import get_settings
from app.pipelines.runner import PIPELINE_ORDER, run_pipelines


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        _write_json(
            {"status": "error", "error": {"code": "VALIDATION_ERROR", "message": message}},
            sys.stderr,
        )
        raise SystemExit(2)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=PIPELINE_ORDER,
        default=None,
        help="run one pipeline instead of all three",
    )
    return parser.parse_args(argv)


async def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        settings = get_settings()
        client = db.get_client()
        summaries = await run_pipelines(
            owned_database=client[settings.mongodb_database],
            competitorscope_database=client[settings.competitorscope_database],
            dct_database=client[settings.dct_database],
            pace_database=client[settings.pace_database],
            only=args.only,
        )
        _write_json({"status": "ok", "pipelines": summaries}, sys.stdout)
        return 0
    except Exception as error:
        _write_json(
            {"status": "error", "error": {"code": "UPSTREAM_UNAVAILABLE", "message": str(error)}},
            sys.stderr,
        )
        return 1
    finally:
        if db.get_client.cache_info().currsize:
            await db.get_client().close()
            db.get_client.cache_clear()


def _write_json(payload: dict[str, object], stream: TextIO) -> None:
    stream.write(json.dumps(payload, default=str, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
