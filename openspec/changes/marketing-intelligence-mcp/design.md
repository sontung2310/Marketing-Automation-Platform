# Design

## Context

Step 1 provides typed repositories over the owned Intelligence DB. The backend
already resolves MCP SDK 2.2.0, but `backend/app/mcp_server/` has no runtime
server yet. The existing agents contract fixes the nine tool names, the
`{results: [...]}` list/search shape, empty-result behavior, and read-only
repository boundary. This design completes the server, validation, operability,
and real-client verification for all of Step 2.

## Goals / Non-Goals

**Goals:**

- Expose the nine CAP-MCP-01 read tools through a dependency-injectable,
  streamable-HTTP `MCPServer` service.
- Enforce tenancy at repository reads, including recommendation lookup through
  the recommendation's session.
- Preserve documented result shapes while returning recoverable validation,
  missing-record, and empty-result responses.
- Make the service runnable at `MCP_URL` in Compose and independently
  verifiable through a real HTTP MCP client and smoke CLI.

**Non-Goals:**

- No agent integration, API route, UI, source-database, write-path, or
  data-contract schema change.
- No `company_id` field on `recommendations`, no seed JSON dependency in MCP
  integration tests, and no in-process-only MCP client test.
- No new MCP error-code set; the server reuses the documented API codes.
- No reliance on MCP SDK pre-handler argument errors for the agent-facing
  validation contract.

## Decisions

### Use the MCP SDK 2.x `MCPServer`

The dependency remains `mcp>=2.2,<3`, which resolves to MCP 2.2.0. The server
uses `MCPServer`, tool descriptions, and
`streamable_http_app(streamable_http_path="/mcp")`. A lightweight application
entrypoint will serve that app with Uvicorn for Compose and test use.

The official [MCP v2 migration guide](https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver)
confirms that `FastMCP` was renamed to `MCPServer`. Pinning `mcp<2` remains
rejected because it would preserve a legacy API against the resolved SDK and
the project's Agents SDK compatibility range.

### Keep repository ownership explicit and derive recommendation tenancy by session

The server factory receives typed repositories and the configured `company_id`.
Each read uses a tenant-filtered repository method. `RecommendationsRepository`
adds a read that performs one aggregation: it matches the requested
recommendation, `$lookup`s `sessions` on `session_id`, unwinds that join, and
matches the joined session's `company_id`. It returns no recommendation when
the session is absent or belongs to another company; the tool boundary maps
that absence to `NOT_FOUND`.

Adding `company_id` to `recommendations` was rejected. It would duplicate the
session ownership already required by data-contract §3.6, require a schema and
migration decision, and allow the two tenant references to diverge. The joined
read preserves the established ownership model without a data-contract change.

### Preserve result and error contracts at the MCP boundary

MCP validates function signatures before calling a handler. Therefore every
tool signature uses plain JSON types (`str | None`, `int | None`, and
`list[str] | None`), never domain enums or bounded Pydantic values. Enum values
remain visible to agents in the generated input schema through an item-level
`Annotated[str, Field(json_schema_extra={"enum": [...]})]` built from the
domain enum registry (for example an `items.enum` list for `activity_types`).

One shared helper parses those raw arguments into the tool's typed Pydantic
argument model and converts `ValidationError` into
`{error: {code: "VALIDATION_ERROR", message: ...}}`. Every handler uses this
one pattern and declares a union of its typed success model and that shared
error model. Every tool is registered with `structured_output=False`: the
installed SDK therefore advertises no output-schema wrapper and returns only
the documented JSON as text content, with `CallToolResult.is_error == false`.
The typed boundary serializer emits public `id` fields rather than Mongo `_id`
aliases. Agents SDK clients retain their default `use_structured_content=False`;
tests parse the text content rather than relying on structured content.

`list_competitors`, `search_competitor_activity`, `search_trends`, and
`search_influencers` always return `{results: [...]}`; an empty list adds the
documented `note` key rather than a fallback. `limit` defaults to 10, values
above 25 are clamped, and `limit < 1` is a validation envelope. `since_days <
1` is likewise a validation envelope for each applicable tool. An empty
`summarize_competitor_activity` window returns its normal JSON summary with
empty `counts` and `recent_items` arrays plus the no-match note. A missing
get-by-ID record returns `{error: {code: "NOT_FOUND", message: ...}}`.

The server has no Mongo query construction or business logic. It translates
typed input and repository models only, retaining the import-linter boundary.

### Exercise a real streamable-HTTP service with isolated data

The MCP integration fixture creates all of its own typed records with dates
relative to its captured `now`; it never reads the seed JSON. It allocates a
database name with a UUID suffix, drops it in teardown, and uses a second
company plus a recommendation whose session belongs to that company for tenant
isolation cases. This permits parallel integration runs without fixed-database
collisions.

The fixture binds a socket on `127.0.0.1` with port `0`, serves the
`streamable_http_app()` through `uvicorn.Server`, waits for readiness, and
connects `MCPServerStreamableHttp` to that URL. It shuts down the server and
socket in teardown. The test therefore proves the client-visible protocol,
including tool discovery and calls, rather than invoking an ASGI app in process.

### Run the service through Compose and a bounded smoke CLI

The MCP Uvicorn process and `streamable_http_app()` both receive `0.0.0.0:8001`
in Compose. Transport-security allowed hosts come from a typed setting rather
than SDK localhost defaults; its values include localhost loopback hosts for
host tools and `mcp:8001` for Compose traffic. The server explicitly enables
that allowlist, so a Host header for the service name is accepted without
opening arbitrary-host access.

Compose adds the MCP service while the API service overrides `MCP_URL` to
`http://mcp:8001/mcp`; host tools retain `.env`'s
`http://localhost:8001/mcp`. The 2.3 verification calls tool listing from
inside the API container through that effective URL.

The smoke CLI accepts the running `MCP_URL`, lists tools, calls all nine, and
exits non-zero for transport errors, unexpected envelopes, absent tool
descriptions, or response-shape violations. It obtains IDs from list/search
responses where available; for `get_recommendation`, where Step 1 seed data has
no persisted recommendation, it calls a synthetic prefixed ID and accepts the
documented `NOT_FOUND` envelope as the expected read-only result.

### Evaluation evidence is not applicable until the agent steps

The evaluation-spec §6 thresholds are for the Router, Strategy and Execution
agents. Step 2 changes no agent prompt, model, skill, agent behavior or eval
harness; those components arrive in Steps 4–6. Its MCP-specific deterministic
evidence is the real-HTTP integration suite and running-service smoke CLI.
Therefore an agent evaluation report is not applicable for this Step; the Step
PR records that rationale alongside the 2-A–2-E command output.

## Risks / Trade-offs

- [A repository query omits tenant scope] → require `company_id` in every
  tenant-owned query, use a separate-company fixture, and test recommendation
  lookup independently from list/search results.
- [A real HTTP fixture leaks a server or database] → bind one owned socket,
  await Uvicorn shutdown, use a UUID database name, and drop it in `finally`.
- [MCP SDK behavior changes] → retain the `<3` upper bound and assert the
  Agents SDK client-visible tool list and responses instead of private SDK
  internals.
- [A handler type causes MCP to reject input first] → keep signatures to plain
  JSON types, advertise enum metadata separately, and prove the JSON
  validation envelope is not an `is_error` result over HTTP.
- [Compose treats `localhost` as the API container] → override the API's
  `MCP_URL` to the `mcp` service name and test that path from inside the API
  container.
- [A running smoke target lacks a recommendation] → treat its expected
  `NOT_FOUND` envelope as a successful call, not as a fabricated record or
  write.

## Migration Plan

1. Implement the 2.1 server, repository reads, and real-HTTP integration
   fixture against the existing MCP 2.x lock.
2. Add 2.2 validation and response-envelope coverage without altering list or
   search result shapes.
3. Add the 2.3 Compose service and smoke CLI, then run them against a running
   local service.
4. Run the MCP tests and `npm run check`; rollback is a normal revert because
   no stored schema or existing service behavior changes.
