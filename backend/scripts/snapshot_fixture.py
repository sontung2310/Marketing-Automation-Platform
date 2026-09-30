"""Build an eval fixture from the committed seed plus the adversarial records.

Run from the repository root with:
    uv run --directory backend python scripts/snapshot_fixture.py --version intelligence_v1

The output is deterministic, so re-running it on an unchanged seed rewrites the same file.
A changed seed or adversarial file needs a new version (evaluation-spec §7.5).
"""

from __future__ import annotations

import argparse
import json
import sys

from app.pipelines.seed.loader import SEED_AUTHORED_AT, load_seed_bundle
from evals.fixture import FIXTURES_DIR, FixtureBundle, fixture_path


def build(version: str) -> FixtureBundle:
    seed = load_seed_bundle(now=SEED_AUTHORED_AT)  # keep the authored timestamps
    adversarial = json.loads((FIXTURES_DIR / "adversarial_v1.json").read_text("utf-8"))
    return FixtureBundle.model_validate(
        {
            "version": version,
            "snapshot_at": SEED_AUTHORED_AT,
            "companies": seed.companies,
            "competitors": seed.competitors,
            "competitor_activities": [
                *seed.competitor_activities,
                *adversarial["competitor_activities"],
            ],
            "trends": [*seed.trends, *adversarial["trends"]],
            "influencers": [*seed.influencers, *adversarial["influencers"]],
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", default="intelligence_v1")
    args = parser.parse_args()
    fixture = build(args.version)
    ids = [r.id for r in (*fixture.competitor_activities, *fixture.trends, *fixture.influencers)]
    if len(ids) != len(set(ids)):
        sys.stderr.write("fixture: duplicate record IDs\n")
        return 1
    path = fixture_path(args.version)
    path.write_text(fixture.model_dump_json(indent=1, by_alias=True) + "\n", encoding="utf-8")
    sys.stdout.write(f"fixture: wrote {len(fixture.ids())} records to {path.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
