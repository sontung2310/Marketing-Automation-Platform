# marketing-intelligence-mcp Specification

## Purpose
Provides the Strategy and Execution agents a tenant-scoped, read-only MCP
service for all Intelligence evidence types, with stable error and operational
contracts for local use.

## Requirements

### Requirement: The MCP exposes documented read tools over streamable HTTP

The running streamable-HTTP MCP service SHALL expose exactly these nine tools:
`get_company_context`, `list_competitors`, `search_competitor_activity`,
`get_competitor_activity`, `summarize_competitor_activity`, `search_trends`,
`search_influencers`, `get_influencer`, and `get_recommendation`. Each tool
MUST have a non-empty description and return JSON-serializable data using the
documented field names and prefixed IDs. Every list/search tool MUST return an
object containing `results`; the empty-result and error rules below extend that
shape rather than replacing it. Tool signatures MUST accept raw JSON argument
types so MCP pre-handler validation cannot bypass the service error contract;
where an argument represents a domain enum, its valid values MUST remain
advertised in the tool input schema.

#### Scenario: A real MCP client lists the semantic tools

- **GIVEN** the service is running on its streamable-HTTP endpoint
- **WHEN** a throwaway Agents SDK `Agent` uses an
  `MCPServerStreamableHttp` client to list available tools without a model call
- **THEN** it receives exactly the nine documented tool names, each with a
  non-empty description

#### Scenario: Activity search returns the requested recent type

- **GIVEN** a test database contains time-relative seeded-equivalent activity
  records and the service is running over HTTP
- **WHEN** a real MCP client calls
  `search_competitor_activity(activity_types=["PRICE_CHANGE"], since_days=30)`
- **THEN** it receives `{results: [...]}` containing only `PRICE_CHANGE`
  records from the last 30 days, newest first, with `act_` IDs

### Requirement: MCP reads are tenant-scoped and repository-backed

The service SHALL scope every read to its configured `company_id`, use only
typed intelligence repositories, and perform no writes. The company-context
tool MUST return the configured company's context. Competitor, activity, trend,
and influencer list/search reads MUST exclude another company's records.
Recommendation lookup MUST derive tenancy through the recommendation's
`session_id`: the repository read SHALL join `sessions` and return no record
unless the joined session belongs to the configured company.

#### Scenario: Cross-tenant list and search records are excluded

- **GIVEN** the owned database contains competitor, activity, trend, and
  influencer records for the configured company and a second company
- **WHEN** a client lists competitors or searches activities, trends, and
  influencers
- **THEN** every returned record belongs to the configured company and no
  cross-tenant ID is present

#### Scenario: Cross-tenant recommendation lookup returns no record

- **GIVEN** a recommendation belongs to a session for another company
- **WHEN** a client calls `get_recommendation` with that recommendation ID
- **THEN** no recommendation body is returned and the missing-record envelope
  specified below has code `NOT_FOUND`

#### Scenario: Company context is tenant-specific

- **GIVEN** two company context documents exist
- **WHEN** `get_company_context` is called for the configured company
- **THEN** the response contains only that company's context fields and ID

### Requirement: MCP result and error envelopes are recoverable

The service SHALL parse raw tool arguments through one shared typed validation
helper. Arguments whose values fit their advertised JSON types but violate a
domain rule MUST return `{error: {code, message}}` with `VALIDATION_ERROR`,
not an MCP `is_error` result, and an unknown ID to a get-by-ID tool MUST return
that envelope with `NOT_FOUND`. Arguments that violate their advertised JSON
types SHALL be rejected by the MCP SDK before the handler as an `is_error`
result. Every tool's
declared return type MUST admit both its success response and this error
envelope. List/search tools SHALL use a default `limit` of 10, return no more
than 25 results when a larger limit is requested, and return `VALIDATION_ERROR`
for `limit < 1`. Tools accepting `since_days` MUST return `VALIDATION_ERROR`
for a value below 1. A valid list/search request with no matches SHALL return
`{results: [], note: "No records matched …"}` and MUST NOT fabricate a
fallback record. When `summarize_competitor_activity` has no activity in its
window, it SHALL return its normal JSON summary with empty `counts` and
`recent_items` arrays and the no-match note.

#### Scenario: Invalid activity type returns a validation envelope

- **GIVEN** the service is running
- **WHEN** a client calls
  `search_competitor_activity(activity_types=["BOGUS"])`
- **THEN** the response is an error object with code `VALIDATION_ERROR` and a
  user-readable message, and the real HTTP client's result is not `is_error`

#### Scenario: A JSON type mismatch is rejected by the SDK

- **GIVEN** the service is running
- **WHEN** a client calls `search_competitor_activity(since_days="abc")`
- **THEN** the MCP SDK returns an `is_error` result before the tool handler

#### Scenario: An unknown record ID returns a missing-record envelope

- **GIVEN** the service is running
- **WHEN** a client supplies an unknown ID to a get-by-ID tool
- **THEN** the response is an error object with code `NOT_FOUND` and a
  user-readable message

#### Scenario: An empty search has an explanatory note

- **GIVEN** the service is running
- **WHEN** a client searches with `query="quantum knitting"`
- **THEN** the response is `{results: [], note: ...}` and no error is raised

#### Scenario: A large limit is capped

- **GIVEN** more than 25 matching records exist
- **WHEN** a client supplies `limit=500` to a list/search tool
- **THEN** at most 25 records are returned

#### Scenario: Invalid lower bounds return validation envelopes

- **GIVEN** the service is running
- **WHEN** a client supplies `limit=0` or `since_days=0` to an applicable tool
- **THEN** the response is an error object with code `VALIDATION_ERROR`

#### Scenario: An empty activity summary remains a summary

- **GIVEN** no activity falls within the requested summary window
- **WHEN** a client calls `summarize_competitor_activity`
- **THEN** the response has empty `counts` and `recent_items` arrays and the
  no-match note, without an error or fabricated activity

### Requirement: MCP is a read-only runtime boundary

The MCP implementation MUST NOT import `pymongo` or `bson`, bypass typed
repositories, or issue writes to owned or source collections. Calling any tool
MUST leave collection contents unchanged.

#### Scenario: Static and runtime checks find no writes

- **GIVEN** the MCP server module and snapshots of relevant collections
- **WHEN** the import-layer check and all nine MCP tools run
- **THEN** the module has no direct MongoDB imports or write calls and the
  snapshots remain unchanged

### Requirement: The MCP service is runnable and smoke-testable locally

The MCP service SHALL listen on `0.0.0.0:8001` in Compose and use a
settings-supplied transport-security host allowlist that includes localhost
loopback hosts and the `mcp` Compose service host. Host tools SHALL retain the
`.env` default `MCP_URL` of `http://localhost:8001/mcp`; the Compose API service
SHALL override its `MCP_URL` to `http://mcp:8001/mcp`. A smoke script SHALL
connect to a running service, list the nine tools, call each one, and exit
non-zero on an unexpected transport, tool-list, or response failure.

#### Scenario: The running service passes the smoke CLI

- **GIVEN** the local Compose MCP service is running at `MCP_URL`
- **WHEN** the smoke CLI runs
- **THEN** it lists all nine described tools, calls each one through MCP, and
  exits successfully only when every response has the documented shape or an
  expected recoverable error envelope

#### Scenario: The API container reaches MCP through the service network

- **GIVEN** the local Compose API and MCP services are running
- **WHEN** a command in the API container lists MCP tools through its effective
  `MCP_URL`
- **THEN** it reaches `http://mcp:8001/mcp` and receives all nine tools
