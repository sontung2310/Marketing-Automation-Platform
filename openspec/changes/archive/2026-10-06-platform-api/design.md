# Design

## Context

Repositories exist for every owned collection (`app/intelligence/repositories/`). `simulate_activity()` already enforces the fictional-only rule. `sse-starlette` is already a dependency. The Step 7 UI (PR #30) calls these paths through `frontend/src/api/` and keeps hand-written types in `types.ts`. The Step 4 branch is editing `repositories/base.py`, `activities.py` and `recommendations.py`, so additions here go at the ends of those files to keep merges trivial.

## Goals / Non-Goals

**Goals:** a live read-only workspace on Vercel, plus Simulate.
**Non-Goals:** run, session and action routes (6.2), the classifier router (6.4–6.5), change streams, auth.

## Decisions

1. **One service module, thin routes.** `app/api/routes/feed.py` validate query and body models and call `app/orchestration/feed.py`, a plain module of async functions over the repositories. Alternative: put the logic in the routes. Rejected because AGENTS §2 says routes only validate and delegate.
2. **Item actions come from one registry.** `ITEM_ACTIONS: dict[ActivityType, list[ItemAction]]` is built from specs §6, with a test asserting every `ActivityType` has an entry. `SOCIAL_POST` resolves its deliverable type from the item's channel through `CHANNEL_POST: dict[Channel, DeliverableType]`. Trends, influencers and recommendations each have a single constant action.
3. **The cursor is base64 of `detected_at|id`.** The query is `{$or: [{detected_at < t}, {detected_at = t, id < i}]}`, sorted by (`detected_at`, `_id`) desc, using the existing `company_detected_at` index.
4. **The activity stream polls instead of using change streams.** It polls every 3 s on the `(detected_at, _id)` keyset, sends a heartbeat every 15 s, and closes after 55 s. Event IDs are opaque positions, and each stream opens with an id-only event plus `retry: 1000`, so even a quiet window leaves the browser a `Last-Event-ID` to resume from (fair-review finding). Serverless functions can't hold a change stream open, and the API contract already defines polling as its fallback. `# ponytail:` switch to change streams if the API moves to a long-lived host.
5. **Vercel hosting.** `backend/index.py` re-exports `app` (a FastAPI entrypoint Vercel recognises). The second Vercel project's root directory is `backend/`; it installs dependencies from `pyproject.toml`/`uv.lock` and uses the Python 3.12 runtime, which `requires-python` allows. The root `vercel.json` adds an external rewrite `/api/:path*` → `https://<api-project>.vercel.app/api/:path*` ahead of the SPA fallback. Alternative: a Python function in the frontend project. Rejected because Vercel would then bundle the Node workspace and the Python service together, and the services are kept self-contained (AGENTS §1).
6. **The OpenAPI check is drift detection, not codegen.** `scripts/export_openapi.py` writes `backend/openapi.json`, and `--check` fails when the committed file is stale. A small Node script (`tools/api-types.mjs`) compares the response-schema field names in `openapi.json` with the matching `types.ts` interfaces and fails on any difference. Both run in `npm run check`. Alternative: replace `types.ts` with `openapi-typescript` output. Deferred, because it would rewrite every Step 7 import for no behaviour change.
7. **Mongo client on serverless.** The existing module-level client is reused across warm invocations. The index creation in `lifespan` is idempotent and cheap.

## Risks / Trade-offs

- [Atlas rejects Vercel's dynamic egress IPs] → the owner allows 0.0.0.0/0 or adds the Atlas Vercel integration (a one-time manual step, documented in the README).
- [Cold starts add 1–2 s to the first request] → acceptable for the PoC, and the 6-A p95 is measured warm.
- [The stream reconnects every 55 s] → the UI already handles `EventSource` reconnects, and `Last-Event-ID` prevents gaps.
- [The Step 4 branch touches the same repositories] → this change only appends new methods. Whichever branch merges second rebases.

## Migration Plan

1. Merge PR #30 (Step 7).
2. Merge this Step's PR.
3. The owner creates the API project and sets its environment variables.
4. Production deploys from `main`.

Rollback: remove the rewrite and the frontend shows error states only.
