"""Scenario 3-A and reference safety for the skill loader."""

from pathlib import Path

import pytest

from app.skills.integrity import read_lock
from app.skills.loader import (
    InvalidReferenceError,
    SkillFormatError,
    load_catalogue,
    parse_skill,
    read_reference,
)


def write_skill(root: Path, skill_md: str) -> Path:
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(skill_md, encoding="utf-8")
    return root


def test_every_vendored_skill_parses_with_folder_name_and_description() -> None:
    catalogue = load_catalogue()
    assert sorted(catalogue) == sorted(read_lock().skills)
    for name, skill in catalogue.items():
        assert skill.meta.name == name
        assert skill.meta.description.strip()
        assert skill.body


@pytest.mark.parametrize(
    "skill_md",
    [
        "# no frontmatter\n",
        "---\nname: demo\n# never closed\n",
        "---\nname: [unclosed\n---\nbody\n",
        "---\nname: demo\n---\nno description\n",
        "---\nname: other\ndescription: wrong folder\n---\nbody\n",
    ],
)
def test_malformed_frontmatter_is_rejected(tmp_path: Path, skill_md: str) -> None:
    with pytest.raises(SkillFormatError):
        parse_skill(write_skill(tmp_path / "demo", skill_md))


def test_reference_inside_skill_is_read() -> None:
    pricing = load_catalogue()["pricing"]
    assert "references/pricing-models.md" in pricing.references
    assert read_reference(pricing, "references/pricing-models.md")


@pytest.mark.parametrize(
    "reference",
    [
        "../social/SKILL.md",
        "references/../../social/SKILL.md",
        "SKILL.md",
        "references/missing.md",
        "/etc/passwd",
    ],
)
def test_reference_outside_references_is_rejected(reference: str) -> None:
    with pytest.raises(InvalidReferenceError):
        read_reference(load_catalogue()["pricing"], reference)


def test_symlink_escaping_the_skill_is_rejected(tmp_path: Path) -> None:
    root = write_skill(tmp_path / "demo", "---\nname: demo\ndescription: d\n---\nbody\n")
    (tmp_path / "secret.md").write_text("secret", encoding="utf-8")
    (root / "references").mkdir()
    (root / "references" / "link.md").symlink_to(tmp_path / "secret.md")
    with pytest.raises(InvalidReferenceError):
        read_reference(parse_skill(root), "references/link.md")
