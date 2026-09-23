# Proposal

Roadmap: 2.1, 2.2, 2.3

## Why

The Strategy and Execution agents need one stable, semantic read boundary over
the normalized Intelligence DB. Step 1 produces the owned records, but no
runtime MCP server exposes them to agents. Completing all of Step 2 supplies
that boundary, its error contract, and an operable local service before skills
and agents depend on it.

## What Changes

- Add an MCP SDK 2.x `MCPServer` streamable-HTTP service at `/mcp` with the
  nine read tools in `docs/agents-spec.md` §3.
- Scope every tool to the configured company through typed intelligence
  repositories. Recommendation lookup derives tenancy from its session in one
  repository aggregate; recommendations do not gain a `company_id` field.
- Keep every list/search result in `{results: [...]}`. Add the documented
  empty-result note, `VALIDATION_ERROR`/`NOT_FOUND` error objects, and the
  default-and-capped limit behavior without changing those result shapes. Tool
  signatures accept raw JSON so the shared argument parser, rather than MCP
  pre-handler validation, returns those envelopes.
- Verify the service with self-contained, time-relative data in a unique,
  disposable test database and a real HTTP MCP client connected to an
  ephemeral loopback port.
- Add the MCP service to Compose at `MCP_URL`, with explicit container-safe
  transport-security hosts and the API's internal `http://mcp:8001/mcp`
  override, plus a smoke CLI that lists and calls every tool against a running
  server.

## Capabilities

### New Capabilities

- `marketing-intelligence-mcp`: CAP-MCP-01, the tenant-scoped, read-only
  semantic MCP surface and its local service operations.

### Modified Capabilities

- None.

## Impact

- Affected code: `backend/app/mcp_server/`, typed intelligence repositories,
  MCP unit/integration tests, `docker-compose.yml`, and a backend smoke script.
- Runtime dependency: the already-resolved official `mcp>=2.2,<3` SDK, plus
  the existing async Mongo repository layer and `uvicorn` transitively supplied
  by MCP.
- No API, agent, UI, source-database, write-path, or data-contract schema
  change. `recommendations` retain their current `run_id` and `session_id`
  ownership model.
