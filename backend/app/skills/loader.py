"""Load and validate the committed marketing-skill catalogue."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

import yaml
from pydantic import BaseModel, Field, field_validator

from app.skills.models import SkillDocument, SkillErrorCode, SkillSummary
from app.skills.registry import SKILL_NAMES

DEFAULT_LIBRARY_ROOT: Final[Path] = Path(__file__).resolve().parent / "library"
PRODUCT_CONTEXT_NOTE: Final[str] = (
    "In this platform, product context comes from the `get_company_context` tool."
)
MAX_SKILL_LOADS: Final[int] = 3


class SkillLoaderError(Exception):
    """A safe, user-facing catalogue or reference failure."""

    def __init__(self, code: SkillErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SkillFrontmatter(BaseModel):
    """The only metadata the runtime contract consumes."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)

    @field_validator("name", "description")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


@dataclass(frozen=True)
class _LoadedSkill:
    name: str
    description: str
    body: str
    references: Mapping[str, str]

    @property
    def summary(self) -> SkillSummary:
        return SkillSummary(name=self.name, description=self.description)


class SkillCatalogue:
    """An immutable, eagerly validated view of the local skill directory."""

    def __init__(self, skills: Mapping[str, _LoadedSkill], library_root: Path) -> None:
        self._skills = MappingProxyType(dict(skills))
        self.library_root = library_root

    @classmethod
    def from_library(
        cls,
        library_root: Path = DEFAULT_LIBRARY_ROOT,
        *,
        expected_names: tuple[str, ...] = SKILL_NAMES,
    ) -> SkillCatalogue:
        root = library_root.resolve()
        if not root.is_dir():
            raise SkillLoaderError("INVALID_SKILL", f"Skill library does not exist: {root}")

        skills: dict[str, _LoadedSkill] = {}
        for child in sorted(root.iterdir(), key=lambda path: path.name):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.is_symlink():
                raise SkillLoaderError(
                    "INVALID_SKILL", f"Skill directory is a symlink: {child.name}"
                )
            skill = _read_skill(child)
            if skill.name in skills:
                raise SkillLoaderError("INVALID_SKILL", f"Duplicate skill name: {skill.name}")
            skills[skill.name] = skill

        expected = set(expected_names)
        missing = sorted(expected - skills.keys())
        extra = sorted(skills.keys() - expected)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if extra:
                details.append(f"extra={extra}")
            raise SkillLoaderError(
                "INVALID_SKILL", f"Skill catalogue mismatch ({', '.join(details)})"
            )
        return cls(skills, root)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))

    def summaries(self, names: frozenset[str] | None = None) -> list[SkillSummary]:
        selected = self._skills.keys() if names is None else names
        return [self._skills[name].summary for name in sorted(selected)]

    def load(self, name: str, reference: str | None = None) -> SkillDocument:
        skill = self._skills.get(name)
        if skill is None:
            raise SkillLoaderError("NOT_FOUND", f"Skill '{name}' was not found")
        if reference is None:
            return SkillDocument(name=skill.name, description=skill.description, body=skill.body)
        body = skill.references.get(reference)
        if body is None:
            raise SkillLoaderError(
                "INVALID_REFERENCE",
                f"Reference '{reference}' is not available inside skill '{name}'",
            )
        return SkillDocument(
            name=skill.name,
            description=skill.description,
            body=body,
            reference=reference,
        )


@dataclass
class SkillLoadSession:
    """Mutable per-run counter; never shared between agent runs."""

    max_loads: int = MAX_SKILL_LOADS
    load_count: int = 0

    def consume(self) -> bool:
        if self.load_count >= self.max_loads:
            return False
        self.load_count += 1
        return True


def _read_skill(skill_root: Path) -> _LoadedSkill:
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        raise SkillLoaderError("INVALID_SKILL", f"Missing SKILL.md for '{skill_root.name}'")
    try:
        metadata, body = _parse_skill_file(skill_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise SkillLoaderError("LOAD_FAILED", f"Could not read '{skill_file}': {exc}") from exc
    if metadata.name != skill_root.name:
        raise SkillLoaderError(
            "INVALID_SKILL",
            f"Skill metadata name '{metadata.name}' does not match folder '{skill_root.name}'",
        )

    references: dict[str, str] = {}
    references_root = skill_root / "references"
    for path in sorted(references_root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if not path.is_file() or path == skill_file:
            continue
        if path.is_symlink():
            raise SkillLoaderError("INVALID_REFERENCE", f"Skill file is a symlink: {path}")
        relative = path.relative_to(skill_root).as_posix()
        try:
            references[relative] = _append_product_context(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise SkillLoaderError("LOAD_FAILED", f"Could not read '{path}': {exc}") from exc
    return _LoadedSkill(
        name=metadata.name,
        description=metadata.description,
        body=_append_product_context(body),
        references=MappingProxyType(references),
    )


def _parse_skill_file(content: str) -> tuple[SkillFrontmatter, str]:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SkillLoaderError("INVALID_SKILL", "SKILL.md must begin with YAML frontmatter")
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing_index is None:
        raise SkillLoaderError("INVALID_SKILL", "SKILL.md frontmatter is not closed")
    try:
        raw_metadata = yaml.safe_load("".join(lines[1:closing_index]))
        metadata = SkillFrontmatter.model_validate(raw_metadata)
    except (yaml.YAMLError, TypeError, ValueError) as exc:
        raise SkillLoaderError("INVALID_SKILL", f"Invalid SKILL.md frontmatter: {exc}") from exc
    body = "".join(lines[closing_index + 1 :]).lstrip("\n")
    if not body.strip():
        raise SkillLoaderError("INVALID_SKILL", "SKILL.md body must not be blank")
    return metadata, body


def _append_product_context(body: str) -> str:
    content = body.rstrip()
    if PRODUCT_CONTEXT_NOTE in content:
        return content
    return f"{content}\n\n{PRODUCT_CONTEXT_NOTE}"
