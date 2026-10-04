# Spec Delta

## MODIFIED Requirements

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
for values outside 1 through 365. Free-text `query` and `topic` arguments
MUST be at most 200 characters, `region` MUST be an ISO 3166-1 alpha-2 code
such as `AU` (so "Australia" is rejected rather than silently matching
nothing), and `competitor_ids` MUST contain
at most 25 values; violations return `VALIDATION_ERROR`. A valid list/search request with no matches SHALL return
`{results: [], note: "No records matched …"}` and MUST NOT fabricate a
fallback record. When `summarize_competitor_activity` has no activity in its
window, it SHALL return its normal JSON summary with empty `counts` and
`recent_items` arrays, an empty `totals_by_competitor` object and the no-match
note. Otherwise `totals_by_competitor` gives each competitor's activity count,
most active first.

Repository failures SHALL be logged with the tool name and returned as a
non-`is_error` `{error: {code: "UPSTREAM_UNAVAILABLE", message}}` envelope.

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
- **THEN** the response has empty `counts` and `recent_items` arrays, an empty
  `totals_by_competitor` and the no-match note, without an error or
  fabricated activity

#### Scenario: A country name is not a region code

- **GIVEN** the service is running
- **WHEN** a client calls `search_influencers(region="Australia")`
- **THEN** the response is an error object with code `VALIDATION_ERROR`

#### Scenario: A repository failure is a logged recoverable envelope

- **GIVEN** a repository read raises an upstream failure
- **WHEN** the corresponding MCP tool is called
- **THEN** the failure is logged with the tool name and the client receives a
  non-`is_error` `UPSTREAM_UNAVAILABLE` envelope
