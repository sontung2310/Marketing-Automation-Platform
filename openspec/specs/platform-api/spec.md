# platform-api Specification

## Purpose
The read side of the Platform API: the company context, competitor feed, insights, simulate trigger and live feed stream that the one-page workspace consumes, shaped exactly as docs/api-contract.md describes.

## Requirements

### Requirement: Company context and tracked keywords

The API SHALL return the configured company's context with `tracked_keywords` and `last_sync_at` (the newest sync time across the intelligence data: competitor activities' `ingested_at` and trends' `computed_at`, or null; influencers carry no sync time). It SHALL replace the tracked keywords from a list of 1–20 terms. Terms are trimmed, must be non-empty and must be unique case-insensitively; the first spelling of a duplicate is kept.

#### Scenario: Seeded company is returned
- **GIVEN** the seeded DB
- **WHEN** `GET /api/company` is called
- **THEN** `200` returns Marketing Eye with the five seeded `tracked_keywords` and a non-null `last_sync_at`

#### Scenario: Keywords are replaced
- **WHEN** `PUT /api/company/tracked-keywords` is called with `[" AI search ", "ai search", "SEO"]`
- **THEN** `200` returns `{tracked_keywords: ["AI search", "SEO"]}`, and a later `GET /api/company` returns the same list

#### Scenario: Invalid keywords are rejected
- **WHEN** the request has an empty list, more than 20 terms or a blank term
- **THEN** `422` returns the standard `VALIDATION_ERROR` envelope and the stored keywords are unchanged

### Requirement: Competitor activity feed

`GET /api/activities` SHALL return the company's activities sorted by `detected_at` desc, then `id` desc. It SHALL accept the CSV filters `activity_types`, `competitor_ids` and `channels`, plus `since`, an opaque `cursor` and `limit` (default 20, max 50). The response SHALL carry `next_cursor` (null on the last page) and `unseen_count`. Each item SHALL include `is_new` (`seen_at` is null) and 1–2 `actions` matching specs §6 for its type. Unknown enum values return `422`.

#### Scenario: Newest first with type-mapped actions (6-A)
- **GIVEN** the seeded DB
- **WHEN** `GET /api/activities?limit=20` is called
- **THEN** items are strictly newest first, each `EXECUTIVE_POST` has the primary action `Draft a CEO post` (Execution, `CEO_POST`) plus `Why it matters`, and each `PRICE_CHANGE` has only `Plan a response` (Strategy)

#### Scenario: Cursor pages through everything once (6-A)
- **WHEN** a client follows `next_cursor` from the first page until it is null
- **THEN** the union of pages equals every activity of the company, with no duplicates or gaps, and p95 latency per page is under 1 s

#### Scenario: Mark seen
- **WHEN** `POST /api/activities/mark-seen {up_to}` is called
- **THEN** every unseen activity detected at or before `up_to` gets `seen_at`, the response is `{updated: n}`, and `unseen_count` drops by n

### Requirement: Simulate and live feed stream

`POST /api/activities/simulate` SHALL create a simulated activity under the simulation-trigger rules and return `201` with the feed item shape. `GET /api/activities/stream` SHALL be a server-sent event stream that emits `activity.created` (feed item shape) for every activity of the company detected after the stream's position, and a heartbeat comment every 15 s. Event IDs are opaque feed positions, and every stream opens with an id-only event carrying its starting position, so a reconnect always has a `Last-Event-ID`. The stream MAY close itself after a bounded time; a reconnect with `Last-Event-ID` resumes from that position with no gaps or duplicates, even when the closed stream sent no activity.

#### Scenario: Simulated signal arrives live (6-B)
- **GIVEN** a client subscribed to `/api/activities/stream`
- **WHEN** `POST /api/activities/simulate {activity_type: "EXECUTIVE_POST"}` is called
- **THEN** `201` returns the item with `is_simulated: true`, and an `activity.created` event with that item's `id` arrives within 3 s

#### Scenario: Routine stream close is invisible to the user
- **GIVEN** a browser subscribed to the activity stream
- **WHEN** the server ends the stream on its bounded schedule and the browser reconnects within 5 s
- **THEN** no "paused" warning appears, and an activity created during the gap still arrives once

#### Scenario: Real competitor cannot be simulated
- **WHEN** simulate names a non-fictional competitor
- **THEN** `422` returns "Simulated activity can only be created for fictional demo competitors" and nothing is written

### Requirement: Insights

`GET /api/trends` (filters `channels`, `direction`, `limit` default 10) SHALL sort by `momentum_pct` desc. `GET /api/influencers` (filters `topic`, `channels`, `limit` default 10) SHALL sort by `relevance_score` desc. `GET /api/recommendations` (`status` default `OPEN`, `limit` default 20) SHALL return the company's persisted recommendations, newest run first. Items SHALL carry the fixed actions `USE_TREND` "Get topic ideas" (Strategy), `DRAFT_OUTREACH` "Draft outreach" (Execution) and `DO_THIS` "Do this" (Execution), respectively.

#### Scenario: Seeded insights load
- **GIVEN** the seeded DB with no Strategy runs yet
- **WHEN** the three endpoints are called
- **THEN** trends and influencers return sorted with their actions, and recommendations return `{items: []}`

### Requirement: Contract types stay in sync

The API's OpenAPI document SHALL be exported to the repository, and `npm run check` SHALL fail when the exported document differs from the running app, or when the frontend's API types no longer match it.

#### Scenario: Drift fails the check
- **GIVEN** a response field renamed in the backend without re-export
- **WHEN** `npm run check` runs
- **THEN** it fails and names the OpenAPI drift

### Requirement: Every error uses the envelope

Every non-2xx response from these routes SHALL use the api-contract error envelope, including request validation failures and unexpected server errors (`INTERNAL`, 500, with a generic message that reveals no internals).

#### Scenario: Unexpected failure
- **GIVEN** a route whose service raises an unexpected exception
- **WHEN** it is called
- **THEN** `500` returns `{error: {code: "INTERNAL", message: "Unexpected server error", details: {}}}`

### Requirement: Researched trends are readable

Trends imported from researched sources SHALL be served alongside pipeline and seed trends: source system `LAST30DAYS`, channel `TIKTOK` and an optional one-line `summary`.

#### Scenario: Shared database trends load
- **GIVEN** the shared database holds `LAST30DAYS` trends with summaries, some on `TIKTOK`
- **WHEN** `GET /api/trends?limit=50` is called
- **THEN** `200` returns every trend, with `summary` where the source provided one
