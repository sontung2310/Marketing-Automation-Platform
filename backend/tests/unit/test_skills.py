"""Unit coverage for the vendored skills catalogue and tool boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.execution.config import EXECUTION_SKILL_ALLOWLIST
from app.agents.strategy.config import STRATEGY_SKILL_ALLOWLIST
from app.skills.integrity import build_lockfile, skill_digest, validate_lockfile
from app.skills.loader import PRODUCT_CONTEXT_NOTE, SkillCatalogue, SkillLoaderError
from app.skills.models import SkillDocument, SkillErrorEnvelope
from app.skills.registry import SKILL_NAMES
from app.skills.tools import build_skill_function_tools, build_skill_toolset

LIBRARY_ROOT = Path(__file__).parents[2] / "app" / "skills" / "library"


def test_catalogue_loads_all_vendored_skills_and_appends_product_context() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)

    assert catalogue.names == tuple(sorted(SKILL_NAMES))
    summaries = catalogue.summaries()
    assert len(summaries) == 12
    assert all(summary.name == summary.name.strip() for summary in summaries)
    assert all(summary.description for summary in summaries)
    document = catalogue.load("product-marketing")
    assert isinstance(document, SkillDocument)
    assert PRODUCT_CONTEXT_NOTE in document.body


def test_catalogue_rejects_metadata_name_that_does_not_match_folder(tmp_path: Path) -> None:
    skill_root = tmp_path / "demo"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: other\ndescription: A demo\n---\n\nBody\n",
        encoding="utf-8",
    )

    with pytest.raises(SkillLoaderError, match="does not match folder"):
        SkillCatalogue.from_library(tmp_path, expected_names=("demo",))


def test_catalogue_rejects_malformed_frontmatter(tmp_path: Path) -> None:
    skill_root = tmp_path / "demo"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text("# Missing frontmatter\n", encoding="utf-8")

    with pytest.raises(SkillLoaderError, match="must begin with YAML frontmatter"):
        SkillCatalogue.from_library(tmp_path, expected_names=("demo",))


def test_reference_cannot_escape_skill_directory(tmp_path: Path) -> None:
    skill_root = tmp_path / "demo"
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A demo\n---\n\nBody\n",
        encoding="utf-8",
    )
    catalogue = SkillCatalogue.from_library(tmp_path, expected_names=("demo",))

    with pytest.raises(SkillLoaderError, match="not available inside"):
        catalogue.load("demo", "../secret.md")


def test_reference_loader_does_not_expose_evals_or_assets() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)

    with pytest.raises(SkillLoaderError, match="not available inside"):
        catalogue.load("social", "evals/evals.json")


def test_execution_cannot_load_strategy_only_pricing_skill() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)
    tools = build_skill_toolset(catalogue, EXECUTION_SKILL_ALLOWLIST)

    result = tools.load_skill("pricing")

    assert isinstance(result, SkillErrorEnvelope)
    assert result.error.code == "NOT_AVAILABLE"
    assert "not available to this agent" in result.error.message


def test_skill_load_budget_rejects_the_fourth_call() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)
    tools = build_skill_toolset(catalogue, EXECUTION_SKILL_ALLOWLIST)

    for name in ("product-marketing", "competitors", "social"):
        assert isinstance(tools.load_skill(name), SkillDocument)
    result = tools.load_skill("emails")

    assert isinstance(result, SkillErrorEnvelope)
    assert result.error.code == "LIMIT_REACHED"


def test_list_skills_is_allowlisted_and_sorted() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)
    tools = build_skill_toolset(catalogue, STRATEGY_SKILL_ALLOWLIST)

    names = [summary.name for summary in tools.list_skills()]

    assert names == sorted(STRATEGY_SKILL_ALLOWLIST)
    assert set(names) == STRATEGY_SKILL_ALLOWLIST


def test_function_tool_factory_exposes_the_two_agent_tools() -> None:
    catalogue = SkillCatalogue.from_library(LIBRARY_ROOT)

    tools = build_skill_function_tools(catalogue, STRATEGY_SKILL_ALLOWLIST)

    assert [tool.name for tool in tools] == ["list_skills", "load_skill"]
    assert all(tool.description for tool in tools)


def test_registry_covers_both_agent_allowlists() -> None:
    assert set(SKILL_NAMES) >= STRATEGY_SKILL_ALLOWLIST
    assert set(SKILL_NAMES) >= EXECUTION_SKILL_ALLOWLIST
    assert "pricing" not in EXECUTION_SKILL_ALLOWLIST
    assert "copywriting" not in STRATEGY_SKILL_ALLOWLIST


def test_lockfile_hashes_are_deterministic_and_detect_edits(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    for name in SKILL_NAMES:
        skill = library / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test {name}\n---\n\nBody\n",
            encoding="utf-8",
        )
    lockfile = tmp_path / "skills.lock.json"
    lockfile.write_text(json.dumps(build_lockfile(library, "commit")), encoding="utf-8")

    assert validate_lockfile(library, lockfile) == []
    digest_before = skill_digest(library / "social")
    (library / "social" / "SKILL.md").write_text(
        (library / "social" / "SKILL.md").read_text(encoding="utf-8") + "edited\n",
        encoding="utf-8",
    )
    digest_after = skill_digest(library / "social")
    errors = validate_lockfile(library, lockfile)

    assert digest_before != digest_after
    assert any("skill 'social' hash mismatch" in error for error in errors)
