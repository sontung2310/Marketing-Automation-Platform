# Tasks

## 1. 6.1 Company, feed and insights endpoints

- [x] 1.1 Add `Company.tracked_keywords` (1–20 unique trimmed terms) and seed the five data-contract §3.1 keywords; verify `test_seed.py` and `test_seed_rules.py` pass and a re-seed is still idempotent.
- [x] 1.2 Add the item-action registry (specs §6) and API schemas for the feed item, trend, influencer, recommendation and company responses; verify a unit test covers every `ActivityType` and the `SOCIAL_POST` channel mapping.
- [x] 1.3 Add the repository methods for a cursor page, `unseen_count`, mark-seen, `last_sync_at` and keyword replacement, appended to their files; verify with integration tests against seeded Mongo.
- [x] 1.4 Add `orchestration/feed.py` and the routes `GET /company`, `PUT /company/tracked-keywords`, `GET /activities`, `GET /trends`, `GET /influencers` and `GET /recommendations`; verify `tests/integration/test_activities_api.py` proves 6-A (ordering, actions, cursor with no gaps or duplicates, p95 < 1 s), plus the keyword and insights scenarios.

## 2. 6.3 Simulate, mark-seen and stream

- [x] 2.1 Add `POST /activities/simulate` (reusing `simulate_activity`) and `POST /activities/mark-seen`; verify the 201 shape, the real-competitor 422 message and `{updated: n}`.
- [x] 2.2 Add `GET /activities/stream` (3 s poll, 15 s heartbeat, 55 s close, `Last-Event-ID` resume); verify an SSE-client integration test proves 6-B (event within 3 s) and that resume emits no duplicates.

## 3. 6.6 Contract sync

- [x] 3.1 Add `scripts/export_openapi.py` (with `--check`), the committed `backend/openapi.json` and `tools/check-api-types.mjs`, both wired into `npm run check`; verify a deliberately renamed field fails the check, then revert it.

## 4. Hosting, docs and close

- [x] 4.1 Add `backend/index.py` and the `/api` rewrite in `vercel.json`; verify locally with `docker compose up` that the UI at :5173 loads real data with fixtures off.
- [ ] 4.2 The owner creates the Vercel API project (root `backend/`), sets `MONGODB_URI`, `MONGODB_DATABASE`, `DEFAULT_COMPANY_ID` and `OPENAI_API_KEY`, and opens Atlas network access; verify on the PR preview that `GET /api/health` reports `mongo: ok`, the feed, trends and influencers render, and Simulate → `EXECUTIVE_POST` shows a live card (screenshot in the PR).
- [ ] 4.3 Update api-contract (stream close and resume), specs §4 deployment row, AGENTS §1, `.env.example` and roadmap (6.1, 6.3, 6.6 brought forward and ticked; 6.2, 6.4, 6.5 follow Steps 4–5); verify the docs match the code.
- [ ] 4.4 Evaluation-spec §6 is not applicable (no agent, skill or MCP change); record that in the PR. Run `npm run check` and `npm run test:integration`; verify both are green and attach the 6-A and 6-B pass lines.
