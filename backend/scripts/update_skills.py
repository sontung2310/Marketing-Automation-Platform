"""Vendor the pinned marketing skills, or verify them offline.

Run from the repository root with:
    uv run --directory backend python scripts/update_skills.py --check
    uv run --directory backend python scripts/update_skills.py --commit <sha> [--skills a b ...]

Update mode is the only code path that contacts GitHub. It replaces the whole
library with the named skills (default: the ones already in the lock) at the
given upstream commit, then rewrites the lock.
"""

from __future__ import annotations

import argparse
import io
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

import httpx

from app.skills.integrity import (
    LIBRARY_DIR,
    LICENSE_FILE,
    LOCK_PATH,
    SkillsLock,
    hash_file,
    hash_tree,
    read_lock,
    verify,
)

SOURCE = "https://github.com/coreyhaines31/marketingskills"


def check() -> int:
    problems = verify()
    for problem in problems:
        sys.stderr.write(f"skills: {problem}\n")
    if not problems:
        sys.stdout.write(f"skills: {len(read_lock().skills)} skills match {LOCK_PATH.name}\n")
    return 1 if problems else 0


def update(commit: str, names: list[str]) -> int:
    response = httpx.get(f"{SOURCE}/archive/{commit}.tar.gz", follow_redirects=True, timeout=60)
    response.raise_for_status()
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(response.content)) as archive:
            archive.extractall(tmp, filter="data")  # "data" rejects links and paths outside tmp
        (upstream,) = Path(tmp).iterdir()
        missing = [n for n in names if not (upstream / "skills" / n / "SKILL.md").is_file()]
        if missing:
            sys.stderr.write(f"skills: not found at {commit}: {', '.join(missing)}\n")
            return 1
        shutil.rmtree(LIBRARY_DIR, ignore_errors=True)
        LIBRARY_DIR.mkdir()
        shutil.copy2(upstream / LICENSE_FILE, LIBRARY_DIR / LICENSE_FILE)
        for name in names:
            shutil.copytree(upstream / "skills" / name, LIBRARY_DIR / name)
    lock = SkillsLock(
        source=SOURCE,
        commit=commit,
        license_sha256=hash_file(LIBRARY_DIR / LICENSE_FILE),
        skills={name: hash_tree(LIBRARY_DIR / name) for name in sorted(names)},
    )
    LOCK_PATH.write_text(lock.model_dump_json(indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"skills: vendored {len(names)} skills at {commit}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify the library offline")
    mode.add_argument("--commit", help="full upstream commit SHA to vendor")
    parser.add_argument("--skills", nargs="+", help="skill names (default: the current lock)")
    args = parser.parse_args()
    if args.check:
        return check()
    return update(args.commit, args.skills or list(read_lock().skills))


if __name__ == "__main__":
    raise SystemExit(main())
