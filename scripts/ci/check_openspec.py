"""Detect OpenSpec conflicts that `openspec validate` does not catch.

Checks, over every active change in openspec/changes/ (archive excluded):

1. Cross-change conflicts: two active changes touch the same requirement of the
   same capability (ADDED twice, MODIFIED/REMOVED/RENAMED by both, or one change
   adds a name another renames to). Whichever is archived second would silently
   overwrite the first.
2. Stale base: a delta MODIFIES/REMOVES/RENAMES a requirement that does not exist
   in openspec/specs/<capability>/spec.md, or ADDS one that already exists.
3. Roadmap link: proposal.md names a roadmap sub-step (e.g. "Roadmap: 4.2") that
   exists in docs/roadmap.md (openspec/config.yaml rules.proposal).

Warnings (non-fatal): two active changes claim the same roadmap sub-step.

Usage: python -m scripts.ci.check_openspec [--root PATH]
Exit code 1 when any error is found.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

SECTION_RE = re.compile(r"^##\s+(ADDED|MODIFIED|REMOVED|RENAMED)\s+Requirements\s*$", re.I)
REQUIREMENT_RE = re.compile(r"^###\s+Requirement:\s*(.+?)\s*$")
RENAME_RE = re.compile(r"^\s*-\s*(FROM|TO):\s*`?###\s+Requirement:\s*(.+?)`?\s*$", re.I)
ROADMAP_ITEM_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s*(\d+\.\d+)\b", re.M)
PROPOSAL_ROADMAP_RE = re.compile(r"roadmap[^\n]*?\b(\d+\.\d+)\b", re.I)


@dataclass
class Delta:
    added: set[str] = field(default_factory=set)
    modified: set[str] = field(default_factory=set)
    removed: set[str] = field(default_factory=set)
    renamed: dict[str, str] = field(default_factory=dict)  # from -> to

    def touched_existing(self) -> set[str]:
        return self.modified | self.removed | set(self.renamed)


def _norm(name: str) -> str:
    return " ".join(name.split()).casefold()


def parse_delta(text: str) -> Delta:
    delta = Delta()
    section: str | None = None
    pending_from: str | None = None
    for line in text.splitlines():
        if match := SECTION_RE.match(line):
            section = match.group(1).upper()
            continue
        if line.startswith("## "):
            section = None
            continue
        if section == "RENAMED":
            if match := RENAME_RE.match(line):
                kind, name = match.group(1).upper(), _norm(match.group(2))
                if kind == "FROM":
                    pending_from = name
                elif pending_from is not None:
                    delta.renamed[pending_from] = name
                    pending_from = None
            continue
        if section and (match := REQUIREMENT_RE.match(line)):
            name = _norm(match.group(1))
            {"ADDED": delta.added, "MODIFIED": delta.modified, "REMOVED": delta.removed}[
                section
            ].add(name)
    return delta


def base_requirements(spec_file: Path) -> set[str]:
    if not spec_file.exists():
        return set()
    return {
        _norm(m.group(1))
        for line in spec_file.read_text().splitlines()
        if (m := REQUIREMENT_RE.match(line))
    }


def active_changes(root: Path) -> list[Path]:
    changes_dir = root / "openspec" / "changes"
    if not changes_dir.exists():
        return []
    return sorted(p for p in changes_dir.iterdir() if p.is_dir() and p.name != "archive")


def check(root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    roadmap = root / "docs" / "roadmap.md"
    roadmap_ids = set(ROADMAP_ITEM_RE.findall(roadmap.read_text())) if roadmap.exists() else set()

    # (capability, requirement) -> [(change, operation)]
    touches: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    steps: dict[str, list[str]] = defaultdict(list)

    for change in active_changes(root):
        proposal = change / "proposal.md"
        if proposal.exists():
            match = PROPOSAL_ROADMAP_RE.search(proposal.read_text())
            if match is None:
                errors.append(
                    f"{change.name}: proposal.md must reference a roadmap sub-step, "
                    'e.g. "Roadmap: 4.2"'
                )
            elif roadmap_ids and match.group(1) not in roadmap_ids:
                errors.append(
                    f"{change.name}: roadmap sub-step {match.group(1)} does not exist in "
                    "docs/roadmap.md"
                )
            else:
                steps[match.group(1)].append(change.name)

        for spec_file in sorted((change / "specs").glob("*/spec.md")):
            capability = spec_file.parent.name
            delta = parse_delta(spec_file.read_text())
            base = base_requirements(root / "openspec" / "specs" / capability / "spec.md")

            for name in sorted(delta.touched_existing() - base):
                errors.append(
                    f"{change.name}: {capability}/'{name}' is modified/removed/renamed but "
                    "does not exist in the main spec (stale base — rebase the change)"
                )
            for name in sorted(delta.added & base):
                errors.append(
                    f"{change.name}: {capability}/'{name}' is ADDED but already exists in "
                    "the main spec (use MODIFIED)"
                )

            for name in delta.added:
                touches[(capability, name)].append((change.name, "ADDED"))
            for name in delta.modified:
                touches[(capability, name)].append((change.name, "MODIFIED"))
            for name in delta.removed:
                touches[(capability, name)].append((change.name, "REMOVED"))
            for old, new in delta.renamed.items():
                touches[(capability, old)].append((change.name, "RENAMED FROM"))
                touches[(capability, new)].append((change.name, "RENAMED TO"))

    for (capability, name), ops in sorted(touches.items()):
        owners = {change for change, _ in ops}
        if len(owners) > 1:
            detail = ", ".join(f"{change} ({op})" for change, op in ops)
            errors.append(
                f"conflict: {capability}/'{name}' is changed by multiple active changes: {detail}"
            )

    for step, names in sorted(steps.items()):
        if len(names) > 1:
            warnings.append(
                f"roadmap sub-step {step} is claimed by multiple changes: {', '.join(names)}"
            )

    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    errors, warnings = check(args.root)
    for warning in warnings:
        print(f"::warning::{warning}")
    for error in errors:
        print(f"::error::{error}")
    changes = len(active_changes(args.root))
    print(f"OpenSpec conflict check: {changes} active change(s), {len(errors)} error(s).")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
