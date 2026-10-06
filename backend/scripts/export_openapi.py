"""Write the Platform API's OpenAPI document to backend/openapi.json.

uv run python scripts/export_openapi.py          # regenerate
uv run python scripts/export_openapi.py --check  # fail when the committed file is stale
"""

import argparse
import json
import sys
from pathlib import Path

from app.api.main import create_app

TARGET = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    document = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != document:
            sys.stderr.write("openapi.json is stale: run `npm run api:export`\n")
            return 1
        return 0
    TARGET.write_text(document)
    return 0


if __name__ == "__main__":
    sys.exit(main())
