"""Exercise every Marketing Intelligence MCP tool through the configured MCP_URL.

Run from the repository root with:
    uv run --directory backend python scripts/mcp_smoke.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TextIO

from agents.mcp import MCPServerStreamableHttp
from mcp.types import CallToolResult, TextContent, Tool

from app.core.config import get_settings
from app.intelligence.models import ActivityType

EXPECTED_TOOL_NAMES = (
    "get_company_context",
    "list_competitors",
    "search_competitor_activity",
    "get_competitor_activity",
    "summarize_competitor_activity",
    "search_trends",
    "search_influencers",
    "get_influencer",
    "get_recommendation",
)


class SmokeContractError(ValueError):
    """A running MCP endpoint violated the smoke CLI's response contract."""


async def run() -> int:
    """Run read-only smoke calls and report one machine-readable summary."""

    try:
        client = MCPServerStreamableHttp(
            {"url": get_settings().mcp_url}, use_structured_content=False
        )
        async with client:
            tools = await client.list_tools()
            _validate_tools(tools)
            calls = await _call_every_tool(client)
        _write_json({"status": "ok", "tools": [tool.name for tool in tools], "calls": calls})
        return 0
    except SmokeContractError as error:
        _write_json(
            {
                "status": "error",
                "error": {"code": "CONTRACT_VIOLATION", "message": str(error)},
            },
            stream=sys.stderr,
        )
        return 1
    except Exception as error:
        _write_json(
            {"status": "error", "error": {"code": "UPSTREAM_UNAVAILABLE", "message": str(error)}},
            stream=sys.stderr,
        )
        return 1


async def _call_every_tool(client: MCPServerStreamableHttp) -> dict[str, str]:
    calls: dict[str, str] = {}
    calls["get_company_context"] = _record(
        await _call(client, "get_company_context", {}), "get_company_context"
    )

    competitors = await _call(client, "list_competitors", {})
    calls["list_competitors"] = _results(competitors, "list_competitors")

    activities = await _call(
        client,
        "search_competitor_activity",
        {"activity_types": [ActivityType.PRICE_CHANGE.value], "limit": 1},
    )
    calls["search_competitor_activity"] = _results(activities, "search_competitor_activity")
    activity_id = _first_result_id(activities, "search_competitor_activity", "act_smoke_missing")
    calls["get_competitor_activity"] = _record_or_expected_not_found(
        await _call(client, "get_competitor_activity", {"activity_id": activity_id}),
        "get_competitor_activity",
        has_source_record=_has_results(activities),
    )

    summary = await _call(client, "summarize_competitor_activity", {})
    calls["summarize_competitor_activity"] = _summary(summary, "summarize_competitor_activity")

    trends = await _call(client, "search_trends", {"limit": 1})
    calls["search_trends"] = _results(trends, "search_trends")

    influencers = await _call(client, "search_influencers", {"limit": 1})
    calls["search_influencers"] = _results(influencers, "search_influencers")
    influencer_id = _first_result_id(influencers, "search_influencers", "inf_smoke_missing")
    calls["get_influencer"] = _record_or_expected_not_found(
        await _call(client, "get_influencer", {"influencer_id": influencer_id}),
        "get_influencer",
        has_source_record=_has_results(influencers),
    )

    calls["get_recommendation"] = _record_or_expected_not_found(
        await _call(client, "get_recommendation", {"recommendation_id": "rec_smoke_missing"}),
        "get_recommendation",
        has_source_record=False,
    )
    return calls


async def _call(
    client: MCPServerStreamableHttp, tool_name: str, arguments: dict[str, object]
) -> dict[str, object]:
    result = await client.call_tool(tool_name, arguments)
    return _json_payload(result, tool_name)


def _validate_tools(tools: list[Tool]) -> None:
    names = tuple(tool.name for tool in tools)
    if names != EXPECTED_TOOL_NAMES:
        raise SmokeContractError(
            f"tool listing expected {EXPECTED_TOOL_NAMES!r}, received {names!r}"
        )
    if not all(tool.description for tool in tools):
        raise SmokeContractError("tool listing expected every tool to have a non-empty description")


def _json_payload(result: CallToolResult, tool_name: str) -> dict[str, object]:
    if result.is_error:
        raise SmokeContractError(f"{tool_name} expected a non-error JSON response")
    if len(result.content) != 1 or not isinstance(result.content[0], TextContent):
        raise SmokeContractError(f"{tool_name} expected one text JSON response")
    payload = json.loads(result.content[0].text)
    if not isinstance(payload, dict):
        raise SmokeContractError(f"{tool_name} expected a JSON object response")
    return payload


def _results(payload: dict[str, object], tool_name: str) -> str:
    results = payload.get("results")
    if not isinstance(results, list):
        raise SmokeContractError(f"{tool_name} expected a results array")
    return "results"


def _first_result_id(payload: dict[str, object], tool_name: str, fallback: str) -> str:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return fallback
    first = results[0]
    if not isinstance(first, dict) or not isinstance(first.get("id"), str):
        raise SmokeContractError(f"{tool_name} expected each result to include a string id")
    return first["id"]


def _has_results(payload: dict[str, object]) -> bool:
    results = payload.get("results")
    return isinstance(results, list) and bool(results)


def _record(payload: dict[str, object], tool_name: str) -> str:
    if not isinstance(payload.get("id"), str):
        raise SmokeContractError(f"{tool_name} expected a record with a string id")
    return "record"


def _record_or_expected_not_found(
    payload: dict[str, object], tool_name: str, *, has_source_record: bool
) -> str:
    error = payload.get("error")
    if error is not None:
        if not isinstance(error, dict) or error.get("code") != "NOT_FOUND":
            raise SmokeContractError(f"{tool_name} expected a NOT_FOUND envelope")
        if has_source_record:
            raise SmokeContractError(
                f"{tool_name} expected the record selected from its non-empty list result"
            )
        return "not_found"
    return _record(payload, tool_name)


def _summary(payload: dict[str, object], tool_name: str) -> str:
    if not isinstance(payload.get("counts"), list) or not isinstance(
        payload.get("recent_items"), list
    ):
        raise SmokeContractError(f"{tool_name} expected counts and recent_items arrays")
    return "summary"


def _write_json(payload: dict[str, object], stream: TextIO = sys.stdout) -> None:
    stream.write(json.dumps(payload, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
