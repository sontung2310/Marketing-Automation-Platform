# Tasks

## Roadmap scenario mapping

| Roadmap scenario | Task(s) that prove it |
|---|---|
| 2-A | 1.6 — real HTTP activity search integration test |
| 2-B | 2.2 — empty-result integration test |
| 2-C | 2.1 and 2.3 — real-client invalid-enum/envelope and bound/cap tests |
| 2-D | 1.7 — MCP layering/read-only test and import-linter contract |
| 2-E | 1.6 and 3.2 — Agents SDK HTTP tool discovery and running-service smoke |

## 2.1 — Server and tools

- [x] 1.1 Update the backend dependency declaration to `mcp>=2.2,<3`,
  regenerate `backend/uv.lock`, and verify the lock resolves MCP 2.2.x with
  `uv tree --directory backend`.
- [ ] 1.2 Add the dependency-injectable MCP SDK 2.x `MCPServer` factory,
  streamable-HTTP app, and Uvicorn entrypoint, registering all nine CAP-MCP-01
  tools with descriptions; use plain JSON signature types while advertising
  domain enum values in each input schema, and verify registration against the
  installed SDK.
- [ ] 1.3 Add typed, tenant-filtered repository reads for company context,
  competitors, activities, trends, and influencers; add a
  `RecommendationsRepository` aggregation that `$lookup`s `sessions` on
  `session_id` and filters the joined `company_id`; verify a cross-tenant
  recommendation returns no model without adding `company_id` to recommendations.
- [ ] 1.4 Implement the nine handlers with documented prefixed-ID fields and
  `{results: [...]}` for every list/search tool; route all raw arguments through
  one shared typed Pydantic parser that returns the `VALIDATION_ERROR` envelope,
  and declare each return as a success/error union accepted by MCP structured
  output; verify unit tests cover each representative result shape and
  repository-only delegation.
- [ ] 1.5 Build the MCP integration fixture with its own typed, time-relative
  records, UUID-suffixed disposable Mongo database, second-company session and
  recommendation, ephemeral `127.0.0.1` Uvicorn server, and
  `MCPServerStreamableHttp` URL client; verify teardown drops the database and
  parallel runs do not share names.
- [ ] 1.6 Add real-HTTP integration tests that prove 2-A's filtered,
  newest-first `PRICE_CHANGE` results and 2-E's nine described tools through
  an Agents SDK client; prove `activity_types=["BOGUS"]` returns the JSON
  `VALIDATION_ERROR` envelope with `is_error == false`; also verify list/search
  exclude cross-tenant competitor, activity, trend, and influencer records and
  a cross-tenant recommendation returns no record.
- [ ] 1.7 Add or extend MCP layering/read-only coverage; verify 2-D through
  the import-linter contract, no direct MongoDB imports or writes, and unchanged
  collection snapshots after all nine calls.

## 2.2 — Validation and errors

- [ ] 2.1 Verify the shared raw-argument parser returns the existing
  `VALIDATION_ERROR` and `NOT_FOUND` codes in `{error: {code, message}}`
  objects; verify invalid `activity_types=["BOGUS"]` over the real HTTP client
  is not an SDK `is_error` result and unknown get-by-ID arguments separately.
- [ ] 2.2 Return `{results: [], note: "No records matched …"}` for valid empty
  list/search results without a fallback; verify 2-B with
  `query="quantum knitting"`.
- [ ] 2.3 Apply `limit=10` defaults and a `25` cap to every limited list/search
  tool; reject `limit < 1` and `since_days < 1` with `VALIDATION_ERROR`, and
  verify 2-C's `limit=500` returns at most 25 records.
- [ ] 2.4 Return an empty `summarize_competitor_activity` window as its normal
  JSON summary with empty `counts` and `recent_items` arrays plus the no-match
  note; verify that response has neither an error nor a fabricated activity.

## 2.3 — Compose and smoke

- [ ] 3.1 Add the MCP service to `docker-compose.yml`, serving on `0.0.0.0:8001`
  with settings-supplied transport-security allowed hosts for localhost and
  `mcp:8001`; override the API service's `MCP_URL` to `http://mcp:8001/mcp`
  while leaving host-tool `.env` defaults unchanged; verify a streamable-HTTP
  client accepts both approved host-header paths.
- [ ] 3.2 Add `backend/scripts/` smoke CLI that lists all nine tools and calls
  each against a running server, obtaining IDs from result lists and accepting
  the expected `NOT_FOUND` recommendation lookup; verify unexpected failures
  exit non-zero and successful 2-E smoke exits zero.
- [ ] 3.3 Verify from inside the running API Compose container that its
  effective `MCP_URL` lists all nine tools through `http://mcp:8001/mcp`; prove
  the container does not use its own loopback endpoint.
- [ ] 3.4 Confirm `docs/agents-spec.md`, `docs/api-contract.md`,
  `docs/data-contract.md`, and `docs/roadmap.md` match the implemented MCP
  contract; update only affected docs and record why the data-contract schema
  remains unchanged.
- [ ] 3.5 Run the applicable MCP/agent evaluation evidence or record a justified
  not-applicable result under evaluation-spec §6; verify the PR meets the
  AGENTS.md §5 requirement for changed MCP tools.
- [ ] 3.6 Run `npm run test:integration`, the running-service smoke CLI, and
  `npm run check` (including `openspec:check`); attach the 2-A–2-E evidence to
  the Step PR before review.
