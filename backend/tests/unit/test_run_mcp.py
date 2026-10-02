"""The per-run MCP wrapper: call limit, trace, events and retrieved IDs."""

import json
from typing import Any

import pytest
from agents.mcp import MCPServerStreamableHttp
from mcp.types import CallToolResult, TextContent

from app.agents.common.context import MAX_MCP_CALLS_PER_RUN, RunContext
from app.agents.common.intents import Intent
from app.agents.common.mcp import RunMCPServer, collect_ids

SEARCH_RESULT = {"results": [{"id": "act_1", "competitor": {"id": "cpt_9"}}, {"id": "act_2"}]}


def context() -> RunContext:
    return RunContext(
        company_id="cmp_marketing_eye", session_id="ses_1", run_id="run_1", intent=Intent.CHAT
    )


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> RunMCPServer:
    async def fake_call(
        self: MCPServerStreamableHttp, name: str, args: dict[str, Any] | None, meta: object = None
    ) -> CallToolResult:
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(SEARCH_RESULT))])

    monkeypatch.setattr(MCPServerStreamableHttp, "call_tool", fake_call)
    return RunMCPServer(context(), "http://mcp.test/mcp")


def test_collect_ids_walks_nested_results() -> None:
    assert collect_ids(SEARCH_RESULT) == {"act_1", "act_2", "cpt_9"}
    assert collect_ids({"error": {"code": "NOT_FOUND"}}) == set()


async def test_call_is_traced_and_ids_are_retrieved(server: RunMCPServer) -> None:
    await server.call_tool("search_competitor_activity", {"since_days": 30})
    ctx = server.context
    assert ctx.mcp_calls == 1
    assert ctx.retrieved_ids == {"act_1", "act_2", "cpt_9"}
    (call,) = ctx.tool_calls
    assert call["tool"] == "search_competitor_activity"
    assert call["result_count"] == 2
    assert ctx.events[-1]["type"] == "agent.tool"


async def test_call_after_the_limit_returns_limit_reached(server: RunMCPServer) -> None:
    server.context.mcp_calls = MAX_MCP_CALLS_PER_RUN
    result = await server.call_tool("search_trends", {})
    (block,) = result.content
    assert isinstance(block, TextContent)
    assert json.loads(block.text)["error"]["code"] == "LIMIT_REACHED"
    assert server.context.tool_calls == []
    assert server.context.retrieved_ids == set()


async def test_a_repeated_identical_call_reuses_the_result(server: RunMCPServer) -> None:
    first = await server.call_tool("get_company_context", {})
    again = await server.call_tool("get_company_context", {})
    other = await server.call_tool("search_trends", {"query": "ai"})
    ctx = server.context
    assert again is first and other is not first
    assert ctx.mcp_calls == 2  # the repeat costs nothing from the run's budget
    assert [c.get("cached", False) for c in ctx.tool_calls] == [False, True, False]
