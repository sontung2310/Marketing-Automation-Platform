from pathlib import Path

MCP_SERVER_ROOT = Path(__file__).parents[2] / "app" / "mcp_server"
MONGO_WRITE_METHODS = (
    ".insert_one(",
    ".insert_many(",
    ".replace_one(",
    ".update_one(",
    ".update_many(",
    ".delete_one(",
    ".delete_many(",
    ".bulk_write(",
)


def test_mcp_server_has_no_direct_mongo_imports_or_write_calls() -> None:
    source = "\n".join(path.read_text() for path in MCP_SERVER_ROOT.glob("*.py"))

    assert "pymongo" not in source
    assert "bson" not in source
    assert not any(method in source for method in MONGO_WRITE_METHODS)
