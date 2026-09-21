"""Fail a PR that changes a contract surface without updating its contract doc.

AGENTS.md §3: docs/api-contract.md, docs/data-contract.md and docs/agents-spec.md
change in the same PR as the code they describe. Add the PR label
`no-contract-change` to bypass when a change is genuinely internal.

Usage: python -m scripts.ci.check_contract_drift --base origin/main [--labels "a,b"]
"""

from __future__ import annotations

import argparse
import subprocess
import sys

PKG = "backend/src/marketing_automation/"
BYPASS_LABEL = "no-contract-change"

# (code path prefixes, contract doc)
RULES: list[tuple[tuple[str, ...], str]] = [
    ((f"{PKG}api/",), "docs/api-contract.md"),
    ((f"{PKG}intelligence/models.py", f"{PKG}intelligence/models/"), "docs/data-contract.md"),
    (
        (
            f"{PKG}mcp_server/",
            f"{PKG}agents/common/schemas.py",
            f"{PKG}agents/strategy/schemas.py",
            f"{PKG}agents/execution/schemas.py",
            f"{PKG}orchestration/router.py",
        ),
        "docs/agents-spec.md",
    ),
]


def changed_files(base: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def find_drift(files: list[str]) -> list[str]:
    changed = set(files)
    problems = []
    for prefixes, doc in RULES:
        hits = [f for f in files if f.startswith(prefixes) and not f.endswith("/__init__.py")]
        if hits and doc not in changed:
            problems.append(f"{doc} was not updated, but its contract code changed: {hits}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--labels", default="")
    args = parser.parse_args(argv)

    if BYPASS_LABEL in {label.strip() for label in args.labels.split(",")}:
        print(f"Contract drift check bypassed by label '{BYPASS_LABEL}'.")
        return 0

    problems = find_drift(changed_files(args.base))
    for problem in problems:
        print(f"::error::{problem}")
    if problems:
        print(f"Update the doc in this PR, or add the '{BYPASS_LABEL}' label if nothing changed.")
        return 1
    print("Contract drift check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
