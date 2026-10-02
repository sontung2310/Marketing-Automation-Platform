"""The Intelligence MCP connection for one run: call limit, tool trace and retrieved IDs."""

import json
import time
from typing import Any

from agents.mcp import MCPServerStreamableHttp
from mcp.types import CallToolResult, TextContent

from app.agents.common.context import MAX_MCP_CALLS_PER_RUN, RunContext

ARGS_SUMMARY_CHARS = 200


def collect_ids(payload: object) -> set[str]:
    """Every `id` value anywhere in a tool's JSON result."""
    if isinstance(payload, dict):
        found = {payload["id"]} if isinstance(payload.get("id"), str) else set()
        return found.union(*(collect_ids(value) for value in payload.values()))
    if isinstance(payload, list):
        return set().union(*(collect_ids(item) for item in payload))
    return set()


def result_payload(result: CallToolResult) -> object:
    text = "".join(block.text for block in result.content if isinstance(block, TextContent))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def result_count(payload: object) -> int:
    if isinstance(payload, dict) and "error" in payload:
        return 0
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return len(payload["results"])
    return 1 if payload else 0


class RunMCPServer(MCPServerStreamableHttp):
    """One per run, so the call counter and trace never leak between runs."""

    def __init__(self, context: RunContext, url: str) -> None:
        super().__init__(
            params={"url": url},
            name="marketing-intelligence",
            cache_tools_list=True,
            client_session_timeout_seconds=30,
        )
        self.context = context
        # Reads are idempotent within a run: a repeated identical call reuses the result.
        self._results: dict[str, CallToolResult] = {}

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None, meta: dict[str, Any] | None = None
    ) -> CallToolResult:
        key = f"{tool_name}:{json.dumps(arguments or {}, sort_keys=True)}"
        if (cached := self._results.get(key)) is not None:
            self._trace(tool_name, arguments, result_payload(cached), duration_ms=0, cached=True)
            return cached
        if self.context.mcp_calls >= MAX_MCP_CALLS_PER_RUN:
            error = {
                "code": "LIMIT_REACHED",
                "message": f"All {MAX_MCP_CALLS_PER_RUN} tool calls are used. Finish with what "
                "you have and record a data gap.",
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({"error": error}))]
            )
        self.context.mcp_calls += 1
        started = time.monotonic()
        result = await super().call_tool(tool_name, arguments, meta)
        payload = result_payload(result)
        if not (isinstance(payload, dict) and "error" in payload):
            self._results[key] = result  # a failed call (e.g. a DB blip) stays retryable
        self.context.retrieved_ids |= collect_ids(payload)
        self.context.tool_results.append(payload)
        self._trace(tool_name, arguments, payload, round((time.monotonic() - started) * 1000))
        return result

    def _trace(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
        payload: object,
        duration_ms: int,
        cached: bool = False,
    ) -> None:
        call: dict[str, object] = {
            "tool": tool_name,
            "args_summary": json.dumps(arguments or {})[:ARGS_SUMMARY_CHARS],
            "duration_ms": duration_ms,
            "result_count": result_count(payload),
        }
        if cached:
            call["cached"] = True
        self.context.tool_calls.append(call)
        self.context.emit("agent.tool", call)
