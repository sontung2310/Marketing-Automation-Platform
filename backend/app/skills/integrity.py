"""Lockfile and content hashes for the vendored skill catalogue."""

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

SKILLS_DIR = Path(__file__).resolve().parent
LIBRARY_DIR = SKILLS_DIR / "library"
LOCK_PATH = SKILLS_DIR / "skills.lock.json"
LICENSE_FILE = "LICENSE"  # upstream MIT license, kept beside the skills


class SkillsLock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    commit: str
    skills: dict[str, str]  # skill name -> tree SHA-256


def hash_tree(root: Path) -> str:
    """SHA-256 over every file's relative path and bytes, in sorted order.

    Dotfiles are skipped so OS litter such as macOS .DS_Store never fails the check.
    """
    digest = hashlib.sha256()
    files = (p for p in root.rglob("*") if p.is_file() and not p.name.startswith("."))
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def read_lock(path: Path = LOCK_PATH) -> SkillsLock:
    return SkillsLock.model_validate_json(path.read_text(encoding="utf-8"))


def verify(library: Path = LIBRARY_DIR) -> list[str]:
    """Return one message per mismatch between the library and its lock; empty means clean."""
    lock = read_lock()
    problems: list[str] = []
    vendored = {p.name for p in library.iterdir() if p.is_dir()}
    problems += [f"{name}: not in lock" for name in sorted(vendored - lock.skills.keys())]
    for name, expected in sorted(lock.skills.items()):
        if name not in vendored:
            problems.append(f"{name}: missing from library")
        elif (actual := hash_tree(library / name)) != expected:
            problems.append(f"{name}: hash mismatch (lock {expected[:12]}, found {actual[:12]})")
    return problems
