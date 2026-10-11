# Proposal

## Why

Step 8 is the last roadmap Step before the client demo: the roadmap's own
success criteria (8-A through 8-F) require a scripted, repeatable demo run,
a reset path, clear failure behaviour, all three eval suites passing their
thresholds on the release commit, a human dry run, and a Lighthouse
accessibility gate. Two of those thresholds are currently open: the Strategy
and Execution judge-score gaps accepted as known PoC gaps after Steps 7b and
5 (design D9 and D12) are exactly what 8-D requires closed, and both
specs already name this as "the target a later Step closes."

## What Changes

- **8.1** A Playwright E2E test scripts the 8-step demo story from
  `docs/specs.md` §7 against the real backend and real OpenAI, runnable
  3× in a row (8-A). It runs on demand (a manual CI workflow and an npm
  script), not on every PR, since every run spends real OpenAI budget.
- **8.2** `backend/scripts/reset_demo.py` re-seeds the database and clears
  sessions, runs, actions and simulated items. A demo runbook section is
  added to the README.
- **8.3** Hardening, scoped to the one real gap found on inspection: a
  failed or timed-out run currently logs no token usage at all, even when
  tokens were spent before the failure (including a burned repair). Fix:
  move the `Usage()` object each agent's `run.py` currently tracks as a
  local variable onto `RunContext` itself, so every OpenAI call updates it
  as it completes, and have `RunService._failed` record it into
  `run.usage` too. The existing upstream-error mapping
  (`UPSTREAM_UNAVAILABLE`), run timeout (`RUN_TIMEOUT_SECONDS`), dead-worker
  detection (`RUN_WALL_CLOCK`) and cost guard (`max_runs_per_day`) already
  meet 8-B, 8-C and the rest of 8.3 and are not reworked. No new retry
  logic is added without evidence from 8-B/8-C that one is needed.
- **8.4** Closes the two accepted quality gaps and re-baselines all three
  suites at 3 repeats (evaluation-spec §5.3, before production):
  - **Strategy** (design D9): price responses that don't weigh ≥2 options;
    padded second signals; focused runs that drift from the focus;
    follow-ups that don't search to complete picks and leak internal
    wording; white space asserted rather than shown.
  - **Execution** (design D12): machine-sounding voice; `CREATE_SIMILAR`
    copying the source's structure; missed length limits; `CEO_POST`
    without a concrete example; unsupported requests that ask instead of
    drafting; advice numbers that read as invented.
  - Each suite's report is attached to the release PR (8-D).
- **8.5** Lighthouse CI runs against the demo environment, wired into the
  `npm run check` Check job; the accessibility category must score ≥ 90
  (8-F, the roadmap's own number) and the score is recorded in the release
  PR. Performance is recorded but not gated (Vercel cold starts make it
  unreliable as a gate). The existing `@axe-core/playwright` suite from
  Step 7 must keep reporting zero violations.

## Capabilities

### New Capabilities

None. Every change either closes an existing requirement's documented gap
or adds test/tooling coverage with no new product behaviour.

### Modified Capabilities

- `run-orchestration`: the run-persistence requirement currently defers
  failed-run token usage to "roadmap 8.3" by name; this change removes that
  deferral and requires usage on every run regardless of outcome.
- `strategy-agent`: the evaluation-threshold requirement currently carries
  a "PoC status" paragraph recording the accepted judge-mean gap (3.87
  against 4.0) as the target a later Step closes; this change closes it and
  that paragraph is removed once a passing 3-repeat run is committed as the
  baseline.
- `execution-agent`: the same pattern for its evaluation-threshold
  requirement (judge mean 3.27 against 4.0, brand voice 2.86 against 3.5).

## Impact

- **Code:** `backend/app/orchestration/run_service.py`,
  `backend/app/agents/common/context.py`, `backend/app/agents/common/repair.py`,
  `backend/app/agents/strategy/run.py`, `backend/app/agents/execution/run.py`
  (usage threading); `backend/app/agents/strategy/instructions.md` and
  `backend/app/agents/execution/instructions.md` (gap-closing prompt fixes);
  `backend/scripts/reset_demo.py` (new); `frontend/e2e/demo.spec.ts` (new).
- **CI:** a new on-demand demo workflow; Lighthouse CI added to the Check
  job.
- **Evaluation data:** `evaluation/reports/baseline_strategy.json` and
  `baseline_execution.json` committed for the first time since Steps 7b/5;
  `evaluation/rubrics/*.calibration.json` unaffected.
- **Docs:** `docs/roadmap.md` (tick 8.1–8.5), `docs/agents-spec.md`,
  `docs/evaluation-spec.md` (3-repeat baseline note), `README.md` (runbook).
- **No API or data-contract changes.** `platform-api` and
  `intelligence-db-foundation` are unaffected.
