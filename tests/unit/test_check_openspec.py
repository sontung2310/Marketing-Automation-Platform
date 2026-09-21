from pathlib import Path

from scripts.ci.check_openspec import check, parse_delta

ROADMAP = "# Roadmap\n- [ ] 4.1 Run service\n- [ ] 4.2 Strategy agent\n- [x] 0.1 Scaffold\n"
BASE_SPEC = "# Strategy\n## Requirements\n### Requirement: Topic recommendations\ntext\n"


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/roadmap.md").write_text(ROADMAP)
    spec = tmp_path / "openspec/specs/strategy-agent/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(BASE_SPEC)
    (tmp_path / "openspec/changes/archive").mkdir(parents=True)
    return tmp_path


def _change(root: Path, name: str, delta: str, proposal: str = "Roadmap: 4.2\n") -> None:
    change = root / "openspec/changes" / name
    (change / "specs/strategy-agent").mkdir(parents=True)
    (change / "proposal.md").write_text(proposal)
    (change / "specs/strategy-agent/spec.md").write_text(delta)


MODIFY = "## MODIFIED Requirements\n### Requirement: Topic recommendations\nnew text\n"


def test_parse_delta_reads_all_sections() -> None:
    delta = parse_delta(
        "## ADDED Requirements\n### Requirement: A\n"
        "## MODIFIED Requirements\n### Requirement: B\n"
        "## REMOVED Requirements\n### Requirement: C\n"
        "## RENAMED Requirements\n- FROM: `### Requirement: D`\n- TO: `### Requirement: E`\n"
    )
    assert delta.added == {"a"}
    assert delta.modified == {"b"}
    assert delta.removed == {"c"}
    assert delta.renamed == {"d": "e"}


def test_single_valid_change_passes(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(root, "strategy-topics", MODIFY)

    assert check(root) == ([], [])


def test_two_changes_modifying_same_requirement_conflict(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(root, "change-a", MODIFY)
    _change(root, "change-b", MODIFY, proposal="Roadmap: 4.1\n")

    errors, _ = check(root)

    assert len(errors) == 1
    assert "conflict" in errors[0]
    assert "change-a" in errors[0]
    assert "change-b" in errors[0]


def test_added_name_colliding_with_rename_target_conflicts(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(root, "adds", "## ADDED Requirements\n### Requirement: Response plans\n")
    _change(
        root,
        "renames",
        "## RENAMED Requirements\n- FROM: `### Requirement: Topic recommendations`\n"
        "- TO: `### Requirement: Response plans`\n",
        proposal="Roadmap: 4.1\n",
    )

    errors, _ = check(root)

    assert any("conflict" in e and "response plans" in e for e in errors)


def test_stale_base_and_duplicate_add_are_errors(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(
        root,
        "stale",
        "## MODIFIED Requirements\n### Requirement: Does not exist\n"
        "## ADDED Requirements\n### Requirement: Topic recommendations\n",
    )

    errors, _ = check(root)

    assert any("stale base" in e for e in errors)
    assert any("already exists" in e for e in errors)


def test_proposal_must_reference_existing_roadmap_step(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(root, "no-ref", MODIFY, proposal="Just a proposal\n")
    errors, _ = check(root)
    assert any("must reference a roadmap sub-step" in e for e in errors)


def test_unknown_roadmap_step_is_error_and_shared_step_warns(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _change(root, "unknown", MODIFY, proposal="Roadmap: 9.9\n")
    errors, _ = check(root)
    assert any("9.9 does not exist" in e for e in errors)

    root2 = _repo(tmp_path / "second")
    _change(root2, "one", "## ADDED Requirements\n### Requirement: X\n")
    _change(root2, "two", "## ADDED Requirements\n### Requirement: Y\n")
    errors, warnings = check(root2)
    assert errors == []
    assert any("4.2 is claimed by multiple changes" in w for w in warnings)
