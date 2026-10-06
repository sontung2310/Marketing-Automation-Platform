# Proposal: Platform API, read side, and the first live website

Roadmap: 6.1, 6.3, 6.6 · CAP-DATA-05, CAP-UI-01

## Why

The Step 7 workspace is built, but the only endpoint behind it is `GET /api/health`. The owner wants a live website on Vercel while Step 4 is still in progress. The read side of the Platform API (company, feed, insights, simulate and the live feed stream) depends only on Steps 1–2, so it can ship now. Run routes (6.2), the classifier router (6.4) and its golden dataset (6.5) wait for the Strategy and Execution agents.

## What Changes

- `GET /api/company` and `PUT /api/company/tracked-keywords`. The `Company` model gains `tracked_keywords`, which data-contract §3.1 already documents, and the seed sets the five documented keywords.
- `GET /api/activities`: filters, an opaque cursor and `unseen_count`. Each item's `actions[]` comes from a registry keyed by activity type, built from specs §6.
- `POST /api/activities/mark-seen`, `POST /api/activities/simulate` (reusing the existing simulation service) and `GET /api/activities/stream` (SSE).
- `GET /api/trends`, `GET /api/influencers` and `GET /api/recommendations`, each with its fixed `actions[]`.
- An OpenAPI export, plus a check that the frontend's hand-written API types still match it (6.6).
- Hosting: the FastAPI app runs as a Vercel Python function in a second Vercel project, rooted at `backend/`. The frontend project rewrites `/api/*` to it, so the browser stays same-origin.
- Roadmap note: 6.1, 6.3 and 6.6 are brought forward. 6.2, 6.4 and 6.5 follow Steps 4–5.

## Capabilities

### New Capabilities
- `platform-api`: the HTTP read side the workspace UI consumes. It covers company, feed, insights, simulate, mark-seen and the activity stream.

### Modified Capabilities
- (none) `simulation-trigger` keeps its rules; this change only exposes them over HTTP.

## Impact

- **Backend:** `app/api/routes/*`, `app/api/schemas/*`, a thin feed service, `Company.tracked_keywords`, two repository methods (cursor page, mark-seen) and `backend/index.py`.
- **Frontend:** none at runtime. Step 7's `src/api/` already calls these paths.
- **Ops:** a new Vercel project for the API. The owner sets the Mongo and OpenAI secrets there and opens Atlas network access.
- **Docs:** api-contract (stream reconnect behaviour), specs §4 deployment row, AGENTS §1 and roadmap.
