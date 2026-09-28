"""Parse the vendored skills and read one skill body or reference safely."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.skills.integrity import LIBRARY_DIR

PRODUCT_CONTEXT_NOTE = (
    "Note: In this platform, product context comes from the `get_company_context` tool."
)
FRONTMATTER_FENCE = "---\n"
REFERENCES_DIR = "references"


class SkillMeta(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


@dataclass(frozen=True)
class Skill:
    meta: SkillMeta
    root: Path
    body: str

    @property
    def references(self) -> list[str]:
        refs = self.root / REFERENCES_DIR
        return sorted(p.relative_to(self.root).as_posix() for p in refs.glob("*") if p.is_file())


class SkillFormatError(ValueError):
    """A vendored SKILL.md has missing or malformed frontmatter."""


class InvalidReferenceError(ValueError):
    """A reference is missing or resolves outside the skill's references folder."""


def parse_skill(root: Path) -> Skill:
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    header, fence, body = text.removeprefix(FRONTMATTER_FENCE).partition(f"\n{FRONTMATTER_FENCE}")
    if not text.startswith(FRONTMATTER_FENCE) or not fence:
        raise SkillFormatError(f"{root.name}: SKILL.md has no frontmatter")
    try:
        meta = SkillMeta.model_validate(yaml.safe_load(header))
    except (yaml.YAMLError, ValidationError) as exc:
        raise SkillFormatError(f"{root.name}: invalid frontmatter: {exc}") from exc
    if meta.name != root.name:
        raise SkillFormatError(f"{root.name}: frontmatter name is {meta.name!r}")
    return Skill(meta=meta, root=root, body=body.strip())


@lru_cache
def load_catalogue(library: Path = LIBRARY_DIR) -> dict[str, Skill]:
    """Every vendored skill by name, parsed once."""
    return {p.name: parse_skill(p) for p in sorted(library.iterdir()) if p.is_dir()}


def read_reference(skill: Skill, reference: str) -> str:
    refs = (skill.root / REFERENCES_DIR).resolve()
    # resolve() follows symlinks and "..", and an absolute reference replaces the base,
    # so one containment check covers every escape.
    path = (skill.root / reference).resolve()
    if not path.is_relative_to(refs) or not path.is_file():
        raise InvalidReferenceError(f"{reference!r} is not one of {skill.references}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidReferenceError(f"{reference!r} is not a text file") from exc
