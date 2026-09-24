"""Refresh or verify the pinned marketing-skill catalogue."""

from __future__ import annotations

import argparse
import io
import json
import logging
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Final

from app.skills.integrity import (
    LOCKFILE_NAME,
    build_lockfile,
    validate_lockfile,
    write_lockfile,
)
from app.skills.registry import SKILL_NAMES

REPOSITORY_URL: Final[str] = "https://github.com/coreyhaines31/marketingskills"
LIBRARY_ROOT: Final[Path] = Path(__file__).resolve().parents[1] / "app" / "skills" / "library"
LOCKFILE: Final[Path] = LIBRARY_ROOT / LOCKFILE_NAME
LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify the committed catalogue")
    mode.add_argument("--update", action="store_true", help="download and replace the catalogue")
    parser.add_argument("--commit", help="upstream commit for --update")
    args = parser.parse_args()

    if args.check:
        errors = validate_lockfile(LIBRARY_ROOT, LOCKFILE)
        if errors:
            for error in errors:
                LOGGER.error(error)
            return 1
        LOGGER.info("Skill catalogue check passed (%d skills)", len(SKILL_NAMES))
        return 0

    commit = args.commit or _locked_commit()
    _update_catalogue(commit)
    LOGGER.info("Updated skill catalogue at %s", commit)
    return 0


def _locked_commit() -> str:
    errors = validate_lockfile(LIBRARY_ROOT, LOCKFILE)
    if errors:
        raise SystemExit("Cannot update without a valid lockfile or --commit")
    return str(json.loads(LOCKFILE.read_text(encoding="utf-8"))["source"]["commit"])


def _update_catalogue(commit: str) -> None:
    archive_url = f"{REPOSITORY_URL}/archive/{commit}.tar.gz"
    with urllib.request.urlopen(archive_url, timeout=30) as response:
        archive_bytes = response.read()
    with tempfile.TemporaryDirectory() as temporary_dir:
        temporary_root = Path(temporary_dir)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
            _extract_safely(archive, temporary_root)
        source_roots = [
            path / "skills" for path in temporary_root.iterdir() if (path / "skills").is_dir()
        ]
        if len(source_roots) != 1:
            raise RuntimeError("Upstream archive has an unexpected top-level layout")
        source_root = source_roots[0]
        archive_root = source_root.parent
        staged_root = temporary_root / "staged-library"
        staged_root.mkdir()
        for name in SKILL_NAMES:
            source_skill = source_root / name
            if not (source_skill / "SKILL.md").is_file():
                raise RuntimeError(f"Upstream skill is missing SKILL.md: {name}")
            shutil.copytree(source_skill, staged_root / name)
        shutil.copy2(archive_root / "LICENSE", staged_root / "UPSTREAM-LICENSE")
        lock = build_lockfile(staged_root, commit)
        for name in SKILL_NAMES:
            target = LIBRARY_ROOT / name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(staged_root / name, target)
        shutil.copy2(staged_root / "UPSTREAM-LICENSE", LIBRARY_ROOT / "UPSTREAM-LICENSE")
        write_lockfile(LOCKFILE, lock)


def _extract_safely(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if not target.is_relative_to(root):
            raise RuntimeError(f"Archive member escapes extraction directory: {member.name}")
        if member.issym() or member.islnk():
            if "/skills/" in member.name:
                raise RuntimeError(f"Archive links are not allowed in skills: {member.name}")
            continue
        if not (member.isdir() or member.isfile()):
            raise RuntimeError(f"Unsupported archive member: {member.name}")
        archive.extract(member, destination)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
