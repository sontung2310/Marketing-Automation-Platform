from scripts.ci.check_contract_drift import find_drift

API = "backend/src/marketing_automation/api/routes/activities.py"


def test_api_change_without_contract_doc_is_flagged() -> None:
    problems = find_drift([API])

    assert len(problems) == 1
    assert "docs/api-contract.md" in problems[0]


def test_api_change_with_contract_doc_passes() -> None:
    assert find_drift([API, "docs/api-contract.md"]) == []


def test_package_init_and_unrelated_files_are_ignored() -> None:
    files = [
        "backend/src/marketing_automation/api/__init__.py",
        "backend/src/marketing_automation/core/config.py",
        "frontend/src/App.tsx",
    ]
    assert find_drift(files) == []


def test_agent_schema_change_requires_agents_spec() -> None:
    problems = find_drift(["backend/src/marketing_automation/agents/strategy/schemas.py"])

    assert problems and "docs/agents-spec.md" in problems[0]
