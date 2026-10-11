# Design

## Context

See proposal.md - Why. Grounding in the current code found that most of
8.3's "hardening" is already built: `run_error()` already maps OpenAI/MCP
failures to `UPSTREAM_UNAVAILABLE` (`app/agents/common/errors.py`),
`RunService.execute()` already enforces a 100s run timeout and `load()`
already detects a dead worker after 120s (`app/orchestration/run_service.py`),
and the cost guard already exists as `max_runs_per_day` / `check_daily_cap`.
The one real gap: `AgentOutcome.usage` is only ever read in `execute()`'s
success branch, so a run that fails after spending tokens (an upstream
error, a timeout, or a repair that still fails `ensure_valid`) persists no
usage at all. `RunContext` itself has no `usage` field - the `Usage()`
object strategy/execution's `run.py` builds is a local variable, invisible
to `RunService` until the agent function returns successfully.

CI today (`.github/workflows/ci.yml`) runs one job, `Check`, which never
touches a live backend, MongoDB or OpenAI: Vitest and the Step 7 Playwright
suite (`frontend/e2e/workspace.spec.ts`) both run against the MSW-fixture
dev server (`VITE_USE_FIXTURES=1`), per `frontend/playwright.config.ts`.
`pytest -m integration` (real MongoDB) and every eval suite (real OpenAI)
are separate npm scripts, run by hand, not part of `check`.

## Goals / Non-Goals

**Goals:**
- Close the one real usage-logging gap without reworking the error/timeout/
  cost-guard machinery that already meets 8-B/8-C.
- Close the Strategy (D9) and Execution (D12) judge-score gaps against
  their *existing* spec requirements - no new product behaviour, no new
  requirements beyond the eval-threshold ones already modified in `specs/`.
- Add the demo E2E test, reset script and Lighthouse gate without adding
  OpenAI cost or flakiness to the required per-PR Check job.

**Non-Goals:**
- No retry/backoff layer for OpenAI or MCP calls. Nothing in the grounding
  or in 8-B/8-C's evidence shows transient failures that a retry would fix
  rather than just report; speculative retry logic is explicitly out of
  scope per the proposal.
- No change to `max_runs_per_day` or the daily-cap mechanism; it already
  satisfies "the cost guard" in 8.3.
- No new capability/spec files. Every change either closes an existing
  requirement's documented gap or adds test/CI tooling with no product-
  behaviour change (8.1, 8.2, 8.5).

## Decisions

### D1 - Usage lives on `RunContext`, not a function-local `Usage()`

Add `usage: Usage = field(default_factory=Usage)` to `RunContext` (the
`agents.Usage` class already imported in `repair.py`). Change
`run_with_repair`'s signature to drop its separate `usage: Usage` parameter
and call `context.usage.add(...)` at the same two call sites it already
updates a local `usage`. `strategy/run.py` and `execution/run.py` drop their
local `usage = Usage()` line and read `usage_summary(context.usage)` when
building `AgentOutcome`. `RunService._failed` gains a `context: RunContext`
argument (it already receives `context` at its call sites) and sets
`run.usage = usage_summary(context.usage)` - the same `usage_summary` helper,
unchanged.

Alternative considered: pass the local `Usage()` object into `_failed` from
each `execute()` exception branch instead of moving it onto `RunContext`.
Rejected - the exception can originate inside `run_with_repair` itself
(e.g. the `TimeoutError` wraps the whole `agents[run.agent](...)` call in
`execute()`), so `execute()` never sees the agent's local `usage` variable
on that path. Putting `usage` on `RunContext`, which every call already
closes over, is the one place all paths can reach it - the smaller diff and
the actual root cause, not a per-call-site patch.

### D2 - D9/D12 closed as prompt/instruction fixes, not new mechanics

Both gap lists (memory `strategy-quality-gap-accepted`,
`execution-quality-gap-accepted`) are judge-score shortfalls against
requirements the specs already state (e.g. "any recommendation responding
to [a price change] weighs the options... and their trade-offs" is already
normative text in `strategy-agent` requirement "Strategy advice is focused
and asked for"). Closing them is instruction-file and few-shot-example work
in `app/agents/strategy/instructions.md` and
`app/agents/execution/instructions.md`, plus any post-validation check that
turns out to catch a gap mechanically (e.g. a length-limit check for
Execution's "missed user length limits" item, mirroring the niche-rule
checks Strategy already has) - not a new agent capability or contract
field. Each gap item gets one instruction/prompt change plus 1-2 new golden
cases that would have caught it, then a suite re-run; no gap item is
"designed" further than that before the eval shows whether it worked.

### D3 - The demo E2E test and Lighthouse run outside the required Check gate

8.1's test needs a live backend, a scratch MongoDB and real OpenAI - the
opposite of what `check` has run since Step 7 (fixtures only, no secrets).
It becomes a second GitHub Actions workflow, `demo-e2e.yml`,
`workflow_dispatch`-only (matches the proposal: on demand, not per-PR), that:
1. runs `backend/scripts/reset_demo.py` against a scratch database (a repo
   secret `DEMO_MONGODB_URI`, never the shared `marketing_automation` DB -
   same scratch-DB discipline Step 7b's evidence used);
2. starts the backend and the MCP server;
3. runs `npx playwright test e2e/demo.spec.ts` with real `OPENAI_API_KEY`,
   `--repeat-each=3` (8-A).

Lighthouse (8.5) stays inside `check` because it needs no OpenAI and no
live backend: it runs `@lhci/cli` (new, one dev dependency - nothing
already installed audits performance/accessibility against a rendered
page) against the *same* fixture-backed `vite` dev server
`playwright.config.ts` already starts (`VITE_USE_FIXTURES=1`), reusing its
`webServer` command instead of inventing a second way to serve the app.
"The running demo environment" in 8-F is read as "the actual rendered app
in a browser," matching 7-A's own note that Lighthouse "stands up the real
served environment" only in the sense of a served page versus Step 7's
in-fixture component checks - not as a requirement to spend OpenAI budget
on every PR for an accessibility score, which audits DOM structure and
contrast, not data freshness. Only the accessibility category is asserted
(`minScore: 0.9`, lhci `assert`); performance is recorded in the report but
not asserted, per the proposal (Vercel cold starts).

### D4 - Baseline repeat count moves to 3 for this release only

Both modified specs (`strategy-agent`, `execution-agent`) and
evaluation-spec §5.3 already name 3 repeats as "before production." Step 8
is that point, so 8.4's re-run uses `--repeats 3` for all three suites and
commits all three baselines together (`baseline_router.json` already
exists at 1 repeat from Step 6 and is superseded at 3). The owner is asked
to confirm the extra OpenAI spend (3× the per-suite cost of every previous
PoC round) before this run, same as the Step 7b pattern of flagging cost
before a paid eval round.

## Risks / Trade-offs

- **[Risk]** D9/D12 prompt fixes might not close every gap item in one
  round, and the owner previously declined to pay for repeated rounds in
  the PoC. → **Mitigation**: fix items in the order the gap lists already
  rank them (worst dimension first), re-run the cheaper 1-repeat suite
  between rounds, and only pay for the 3-repeat release baseline once
  1-repeat passes every threshold - mirrors the existing PoC-cost discipline
  (evaluation-spec §5.3).
- **[Risk]** `@lhci/cli` against fixtures, not a live backend, could miss
  an accessibility issue that only appears with real data shapes (e.g. a
  very long competitor name overflowing a card). → **Mitigation**: the
  existing `@axe-core/playwright` suite (Step 7, same fixtures) already
  covers structural a11y; Lighthouse adds the numeric score 8-F asks for,
  not new coverage. A real-data a11y regression is still caught by 8.1's
  demo E2E run against the live environment, which keeps the Step 7 axe
  check active in its own assertions.
- **[Risk]** Moving `Usage` onto `RunContext` means two unrelated code
  paths (strategy and execution `run.py`) share one mutable object across
  the run. → **Mitigation**: `RunContext` is already per-run and
  single-use (a new one is built in `RunService.prepare()` for every run),
  so there is no cross-run or concurrent-write risk; this matches how
  `retrieved_ids` and `tool_calls` already accumulate on the same object.

## Migration Plan

No data migration. `Run.usage` already exists as an optional field
(`app/intelligence/models.py`); failed runs persisted before this change
simply have no `usage`, which stays valid (the field is optional). Roll out
is a normal PR merge; rollback is a normal revert, since no stored data
format changes.
