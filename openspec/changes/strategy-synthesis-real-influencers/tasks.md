# Tasks

## 1. Real influencers in the data (Roadmap 7.10)

- [x] 1.1 In `pipelines/sources/dct.py`, set `DCT_CANDIDATE_LIMIT = 10`, sort
  by score, then followers desc, then `_id`, and read `profile.avatar_url`
  (D6). Add `avatar_url: str | None` to `Influencer`. Verify with a unit
  test on the ranking (a tie at one score orders by followers; a missing
  follower count sorts last).
- [x] 1.2 In `pipelines/influencers.py`, delete owned `DCT` influencers that
  are not in the selected set and report a `deleted` count. Verify with an
  integration test: two runs converge to exactly 10 records, and a record
  that drops out is deleted (7b-A).
- [x] 1.3 Remove `influencers.json` from the seed bundle. The seed writer
  deletes `MOCK_SEED` influencers, and the validator drops the influencer
  minimums. Verify with a seed test where `MOCK_SEED` influencers are gone
  and `DCT` influencers are untouched, and `seed_db.py --validate` passes.
- [x] 1.4 Sort the repository's influencer queries by `relevance_score`
  desc, then `followers` desc, and return `avatar_url` from
  `GET /api/influencers`. Re-export `openapi.json` and the frontend types.
  Verify that `test_activities_api.py` asserts the order and the field, and
  that `npm run api:check` passes.
- [x] 1.5 Run `seed_db.py` and `run_pipelines.py --only influencers`
  against a scratch database (`MONGODB_DATABASE=marketing_automation_7b`).
  The shared `marketing_automation` database waits until after merge,
  because `main`'s models forbid the new `avatar_url` field (design
  Migration Plan). Verify with the pipeline log plus a Mongo count:
  10 `DCT` and 0 `MOCK_SEED` influencers, with avatars (7b-A evidence).

## 2. Influencer avatars in the table (Roadmap 7.11)

- [x] 2.1 Add a DS `Avatar` (lazy image, empty `alt`, token size and radius,
  monogram fallback on a null URL or `onError`) and use it in
  `InfluencerTable` (D7). Verify with a Vitest test of the three cases from
  the workspace-ui scenario, plus the axe scan in the existing Playwright
  load test (7b-B).

## 3. Strategy synthesis (Roadmap 7.12)

- [ ] 3.1 Vendor `marketing-psychology` at the pinned commit with
  `update_skills.py` and add it to the Strategy allowlist only. Verify that
  `npm run skills:check` passes and `test_skills_integrity.py` counts 13
  skills.
- [ ] 3.2 Add `Intent.STRATEGY_SYNTHESIS`, `TriggerKind.COMPANY` and
  `TriggerAction.GENERATE_STRATEGY`. Remap `RESPONSE_PLAN` and `USE_TREND`
  in `TRIGGER_ROUTES`, and add the `COMPANY` resolver to `references.py`
  (D1). Verify with `test_routing.py` and `test_run_references.py` (a
  foreign company ID is rejected).
- [ ] 3.3 Add `insight` and `audience` to `Recommendation`, the persisted
  record and `GET /recommendations`, with `normalise()` caps and an
  empty-string default on read (D2). Re-export the API types. Verify with
  `test_strategy_validation.py` and `npm run api:check`.
- [ ] 3.4 Extend `contract_problems()` with the count cap and the niche rule.
  Record `activity_competitors` in `agents/common/mcp.py` (D3). Verify with
  unit tests: a single-signal recommendation, two activities from one
  competitor, a missing insight or audience, and 6 recommendations each
  produce a problem; `MONITOR` is exempt.
- [ ] 3.5 Rewrite `instructions.md`:
  - the `STRATEGY_SYNTHESIS` row;
  - the expert method and insight template (D4);
  - `WHY_IT_MATTERS` with no recommendations;
  - price moves as one card weighing options;
  - counts aimed at 1–3 with a maximum of 5;
  - no window widening for synthesis.

  Verify with the live `test_strategy_live.py`, updated for an unfocused and
  a price-change-focused synthesis (7b-C, 7b-D).

## 4. One set and the panel (Roadmap 7.13)

- [ ] 4.1 Make `supersede_open` company-wide, with its index on
  `{company_id, status}` (D5). Verify with `test_run_service.py`: session
  B's run supersedes session A's set, and a factual answer keeps it.
- [ ] 4.2 Mark the trigger recommendation `DONE` after a successful
  Execution run with a deliverable, guarded on `OPEN` (D5). Verify with
  `test_run_service.py` (both the button and `#N`) and confirm that a failed
  run keeps it `OPEN` (7b-E).
- [ ] 4.3 Add **Generate strategy** with its disabled and working state to
  the `StrategyPanel` header, and show the insight and audience on cards and
  in `RecommendationSheet` (D7). Verify with Vitest for the card and the
  button state, and with Playwright for generate → the new set only, and Do
  this → send → the card leaves (7b-C, 7b-E).

## 5. Evaluation, docs and evidence (Roadmap 7.14)

- [ ] 5.1 Rewrite the affected `strategy.jsonl` cases and add `ST-SYNTH`
  (D8). Add the `niche_signals` check and the rubric's niche standard. Get
  the owner's approval of the rewritten cases before running. Verify that
  `test_golden_strategy.py` passes the coverage and schema checks.
- [ ] 5.2 Run the Strategy eval suite (`python -m evals.cli run --suite
  strategy --repeats 1`), judge it with the `eval-judge` skill, and build
  the report. Verify that every evaluation-spec §6 Strategy threshold holds,
  then commit the report as `baseline_strategy.*` (7b-F).
- [ ] 5.3 Run the Router suite to confirm the remapped triggers left chat
  routing unchanged. Verify that the router thresholds hold.
- [ ] 5.4 Update the docs:
  - agents-spec §4.1, §5.1 and §6;
  - data-contract §3 (recommendations, influencers), §4.2 and §5;
  - api-contract (trigger kinds, recommendations, influencers);
  - ui-spec §3 (avatars, Generate strategy, card fields);
  - evaluation-spec §3.2;
  - the roadmap: tick Step 7b's sub-steps 7.10–7.14 (added with this
    change) with their evidence.

  Verify with `npm run openspec:check`.
- [ ] 5.5 Run `npm run check` green and capture live evidence for
  7b-A through 7b-E against the running environment (screenshots of the
  panel and table, plus run JSON). Attach it to the Step PR.
