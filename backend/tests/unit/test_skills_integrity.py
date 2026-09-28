"""Scenario 3-D: the vendored skills match their lock, and any hand edit is caught."""

import shutil
from pathlib import Path

import pytest

from app.skills.integrity import LIBRARY_DIR, verify


@pytest.fixture
def library(tmp_path: Path) -> Path:
    copy = tmp_path / "library"
    shutil.copytree(LIBRARY_DIR, copy)
    return copy


def test_committed_library_matches_lock() -> None:
    assert verify() == []


def test_dotfiles_are_ignored(library: Path) -> None:
    (library / "social" / ".DS_Store").write_bytes(b"\0")
    assert verify(library) == []


def test_hand_edit_is_reported(library: Path) -> None:
    with (library / "social" / "SKILL.md").open("a", encoding="utf-8") as file:
        file.write("\nedited by hand\n")
    assert [p.split(":")[0] for p in verify(library)] == ["social"]
    assert "hash mismatch" in verify(library)[0]


def test_missing_and_extra_skills_are_reported(library: Path) -> None:
    shutil.rmtree(library / "emails")
    (library / "seo-audit").mkdir()
    assert verify(library) == ["seo-audit: not in lock", "emails: missing from library"]
