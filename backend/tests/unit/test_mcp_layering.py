from pathlib import Path

from app.intelligence.repositories.base import Repository

MCP_SERVER_ROOT = Path(__file__).parents[2] / "app" / "mcp_server"
PYMONGO_WRITE_METHOD_NAMES = (
    "insert_one",
    "insert_many",
    "replace_one",
    "update_one",
    "update_many",
    "delete_one",
    "delete_many",
    "bulk_write",
)
REPOSITORY_WRITE_METHOD_NAMES = tuple(
    name for name in ("upsert", "upsert_by_source", "ensure_indexes") if name in Repository.__dict__
)
FORBIDDEN_WRITE_METHODS = tuple(
    f".{name}(" for name in (*REPOSITORY_WRITE_METHOD_NAMES, *PYMONGO_WRITE_METHOD_NAMES)
)


def test_mcp_server_has_no_direct_mongo_imports_or_write_calls() -> None:
    source = "\n".join(path.read_text() for path in MCP_SERVER_ROOT.rglob("*.py"))

    assert "pymongo" not in source
    assert "bson" not in source
    assert not any(method in source for method in FORBIDDEN_WRITE_METHODS)
