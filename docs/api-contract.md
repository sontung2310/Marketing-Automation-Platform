# API Contract — Platform API (FastAPI)

> Parent: [specs.md](specs.md). This contract is the single source of truth
> between `frontend/` and `backend/`. `frontend/src/api/` is the only frontend
> module that knows these shapes. Change this file in the same PR as any API
> change.

Base path: `/api`. JSON uses `snake_case`. Timestamps are ISO-8601 UTC.
The PoC has no auth. `company_id` comes from `DEFAULT_COMPANY_ID`, and
endpoints accept an optional `company_id` query parameter for future tenancy.

## Error envelope

```json
{ "error": { "code": "NOT_FOUND", "message": "Activity act_01J… not found", "details": {} } }
```

Codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409),
`UPSTREAM_UNAVAILABLE` (503: Mongo, MCP or OpenAI unreachable), `INTERNAL`
(500). The UI shows `message` verbatim. A failed run's `run.failed` event and
`error` field may also carry `UNGROUNDED_OUTPUT` (it cited evidence no tool
returned, even after one repair), `INVALID_OUTPUT` (it broke the output
contract, even after one repair) or `CANCELLED` (client disconnect or timeout).

The Marketing Intelligence MCP reuses the `VALIDATION_ERROR` and `NOT_FOUND`
code strings in its text-JSON tool envelopes; this does not change the
Platform API's HTTP status mapping.

---

## Health and meta

### `GET /health`
Returns `200 {status: "ok", mongo: "ok|down", mcp: "ok|down", openai: "configured|missing"}`.

### `GET /company`
Returns `200` with the company context (see data-contract §3.1), plus
`tracked_keywords` and `last_sync_at` (the newest `ingested_at` across the
intelligence collections).

### `PUT /company/tracked-keywords`
Replaces the configured company's social-listening keywords.

Request:

```json
{ "tracked_keywords": ["Marketing Strategy", "Digital Marketing Trends", "AI in Marketing"] }
```

The list must contain 1–20 non-empty terms. Terms are trimmed and must be
unique case-insensitively; the first trimmed spelling is preserved. A valid
request returns `200 { "tracked_keywords": [...] }`. Invalid input returns
the standard `VALIDATION_ERROR` envelope; a missing configured company returns
`NOT_FOUND`. Updating these terms does not change competitor-feed filters.

## Competitor activity feed

### `GET /activities`
Query: `activity_types` (CSV), `competitor_ids` (CSV), `channels` (CSV),
`since` (ISO), `cursor` (opaque), `limit` (default 20, max 50).

`200`:
```json
{
  "items": [{
    "id": "act_…", "competitor_id": "cpt_…", "competitor_name": "Brightlane Marketing",
    "activity_type": "EXECUTIVE_POST", "channel": "LINKEDIN",
    "title": "…", "summary": "…", "url": "https://…|null",
    "author": {"name": "…", "role": "CEO"} ,
    "price": null, "engagement": {"likes": 312, "comments": 41, "shares": 18},
    "detected_at": "…", "is_mock": true, "is_simulated": false, "is_new": true,
    "actions": [
      {"action": "CREATE_SIMILAR", "label": "Draft a CEO post", "agent": "EXECUTION", "deliverable_type": "CEO_POST", "primary": true},
      {"action": "WHY_IT_MATTERS", "label": "Why it matters", "agent": "STRATEGY", "primary": false}
    ]
  }],
  "next_cursor": "…|null",
  "unseen_count": 3
}
```
Items are sorted by `detected_at` desc, then `id` desc. `actions` is computed
server-side from the mapping in specs §6, so the UI holds no routing logic.
`is_new` means `seen_at` is null.

### `POST /activities/mark-seen`
Request: `{ "up_to": "ISO timestamp" }`. Response: `200 {updated: n}`.

### `GET /activities/stream` (SSE)
Emits `activity.created` with the same item shape as above whenever a new
activity is ingested or simulated. Sends a heartbeat comment every 15 s. It
is implemented with a MongoDB change stream on `competitor_activities`, and
falls back to 3 s polling when change streams are unavailable.

### `POST /activities/simulate`
Request: `{ "activity_type": "EXECUTIVE_POST" | null, "competitor_id": "cpt_…" | null }`
(null means random among the fictional competitors). The endpoint creates a
record from a simulation template (`is_simulated: true`, `source.system:
SIMULATED`) and returns `201` with the item. It never targets a
non-fictional competitor. Asking for one returns `422` with the message
"Simulated activity can only be created for fictional demo competitors".

## Insights

### `GET /trends`
Query: `channels`, `direction`, `limit` (default 10). Response: `200 {items: [trend]}`,
sorted by `momentum_pct` desc. Each item has `actions: [{action: "USE_TREND", label: "Get topic ideas", agent: "STRATEGY"}]`.

### `GET /influencers`
Query: `topic`, `channels`, `limit`. Response: `200 {items: [influencer]}`, sorted
by `relevance_score` desc. Each item has `actions: [{action: "DRAFT_OUTREACH", label: "Draft outreach", agent: "EXECUTION"}]`.

### `GET /recommendations`
Query: `status` (default `OPEN`), `limit`. Returns the persisted Strategy
recommendations, newest run first, for the Strategy panel. Each item includes
`run_id`, `ordinal`, `next_action` and `run_label`, plus
`actions: [{action: "DO_THIS", label: "Do this", agent: "EXECUTION"}]`.

`run_label` names the run that produced the recommendation, for the Strategy
panel's grouping header — the intent and the triggering item's type, for
example `Plan a response · PRICE_CHANGE`. It is derived server-side from the
run's `intent` and `trigger`; the UI groups by `run_id` when it is absent.

## Agent runs

### `POST /runs`
Starts a run. It returns immediately, and progress arrives over SSE.

Request (exactly one of `message` / `trigger`):
```json
{
  "session_id": "ses_…|null",
  "message": "Write a blog about AI search for B2B founders",
  "agent_hint": "AUTO | STRATEGY | EXECUTION",
  "trigger": { "kind": "FEED_ACTION|RECOMMENDATION|TREND|INFLUENCER", "ref_id": "act_…", "action": "CREATE_SIMILAR" }
}
```

Responses:

- `202 {run_id, session_id, agent, intent, route: {method: "DETERMINISTIC|CLASSIFIER|EXPLICIT", reason, confidence}}`
- `200 {run_id: null, session_id, route: {...}, response: {status: "NEEDS_CLARIFICATION"|"OUT_OF_SCOPE", message, clarification_options: []}}`.
  The router answered without an agent run.
- `404` if the trigger `ref_id` doesn't exist. `422` if both or neither of
  `message`/`trigger` are given.

### `GET /runs/{run_id}/events` (SSE)
Event types. `data` is JSON, and every event has `run_id`, `seq` and `ts`.

| Event | Data | UI use |
|---|---|---|
| `run.started` | `{agent, intent, route}` | Run header |
| `agent.step` | `{label}`, e.g. "Loading company context", "Searching competitor activity", "Loading skill: social" | Progress list |
| `agent.tool` | `{tool, args_summary, duration_ms, result_count, cached?}` (`cached: true` when a repeated identical call reused the run's earlier result) | Collapsible trace |
| `agent.text_delta` | `{text}` (optional, for `message`/`answer` only) | Live headline |
| `output.final` | `StrategyOutput` or `ExecutionOutput`, plus persisted IDs (`recommendation_ids` / `deliverable_id`, `proposed_action_ids`) | Result cards |
| `run.failed` | `{code, message}` | Error state |
| `run.completed` | `{status, duration_ms, usage}` | Closes the stream |

A client that reconnects with `Last-Event-ID` gets the missed events replayed
from `runs.events`.

### `GET /runs/{run_id}`
Full persisted run, for reloads and evals.

### `GET /sessions/{session_id}`
`{id, runs: [run summary + output]}`, oldest first. Used to restore the
workspace after a page refresh (the session ID is kept in `localStorage`).

## Proposed actions

### `POST /actions/{action_id}/approve`
Request: optional `{ "payload_overrides": { "scheduled_for": "…" } }`. The
endpoint validates the payload, runs the mock connector and returns `200` with
the action (`status: EXECUTED`, `receipt`). It returns `409` if the action is
not `PROPOSED`.

### `POST /actions/{action_id}/discard`
Returns `200` with the action (`status: DISCARDED`), or `409` if the action
is not `PROPOSED`.

### `GET /actions?status=`
The action log (used in the workspace's "Action log" disclosure).
