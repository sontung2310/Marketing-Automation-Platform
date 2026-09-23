"""Deterministic hashing and lockfile validation for vendored skills."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.skills.registry import SKILL_NAMES

LOCKFILE_NAME = "skills.lock.json"


def skill_digest(skill_root: Path) -> str:
    """Hash relative paths and bytes in deterministic order."""

    digest = hashlib.sha256()
    for path in _skill_files(skill_root):
        relative = path.relative_to(skill_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def read_lockfile(lockfile: Path) -> dict[str, Any]:
    try:
        raw = json.loads(lockfile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read lockfile {lockfile}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Lockfile must contain a JSON object")
    return raw


def validate_lockfile(library_root: Path, lockfile: Path) -> list[str]:
    """Return all integrity errors; an empty list means the lock is valid."""

    errors: list[str] = []
    try:
        lock = read_lockfile(lockfile)
    except ValueError as exc:
        return [str(exc)]

    source = lock.get("source")
    if not isinstance(source, dict) or not source.get("commit"):
        errors.append("lockfile source.commit is missing")
    entries = lock.get("skills")
    if not isinstance(entries, dict):
        return [*errors, "lockfile skills must be an object"]
    expected = set(SKILL_NAMES)
    actual = set(entries)
    for name in sorted(expected - actual):
        errors.append(f"missing lock entry for skill '{name}'")
    for name in sorted(actual - expected):
        errors.append(f"unexpected lock entry for skill '{name}'")

    for name in SKILL_NAMES:
        entry = entries.get(name)
        skill_root = library_root / name
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            errors.append(f"skill '{name}' has no sha256 lock value")
            continue
        if not skill_root.is_dir():
            errors.append(f"skill '{name}' directory is missing")
            continue
        try:
            actual_digest = skill_digest(skill_root)
        except OSError as exc:
            errors.append(f"skill '{name}' could not be hashed: {exc}")
            continue
        if actual_digest != entry["sha256"]:
            errors.append(
                f"skill '{name}' hash mismatch: expected {entry['sha256']}, got {actual_digest}"
            )
    actual_dirs = {
        path.name
        for path in library_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    }
    for name in sorted(actual_dirs - expected):
        errors.append(f"unexpected skill directory '{name}'")
    return errors


def build_lockfile(library_root: Path, commit: str) -> dict[str, Any]:
    return {
        "source": {
            "repository": "https://github.com/coreyhaines31/marketingskills",
            "commit": commit,
        },
        "skills": {
            name: {"path": name, "sha256": skill_digest(library_root / name)}
            for name in SKILL_NAMES
        },
    }


def write_lockfile(lockfile: Path, content: dict[str, Any]) -> None:
    lockfile.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")


def _skill_files(skill_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(skill_root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if path.is_symlink():
            raise OSError(f"symlinks are not allowed in vendored skills: {path}")
        if path.is_file():
            files.append(path)
    return files
