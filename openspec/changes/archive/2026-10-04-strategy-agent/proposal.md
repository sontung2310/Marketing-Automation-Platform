# Proposal

## Why

Roadmap: 4.1, 4.2, 4.3, 4.4. The platform can retrieve evidence (Step 2) and
methods (Step 3), but nothing yet answers "what should we do?". This Step
delivers the Marketing Strategy Agent and proves it with a golden dataset, so
Execution (Step 5), the API (Step 6) and the UI build on a measured agent.

## What Changes

- **Run service (4.1):** an in-process service that starts a run from a UI
  trigger or a chat message, routes UI triggers deterministically, resolves
  referenced records, persists the session, the run and its event log, and
  records tool calls and skill loads. No HTTP yet.
- **Strategy agent (4.2):** OpenAI Agents SDK agent with instructions, the
  Intelligence MCP tools, `load_skill`, the run limits, the `StrategyOutput`
  contract, a single grounding-repair retry and recommendation persistence.
  Default agent model `gpt-5.6-luna` (`OPENAI_MODEL_AGENT`).
- **Eval harness (4.3):** loads a frozen fixture into a throwaway database,
  runs cases against the real agent and MCP, applies the deterministic checks
  and writes a report. Adds fixture `intelligence_v1` (seed + adversarial
  records).
- **Claude as judge (4.3, decision 2026-09-29):** the LLM-as-judge step is
  performed by Claude subagents in a Claude Code session over saved run
  outputs, using the rubric, instead of an OpenAI judge model. Deterministic
  checks stay in code. This replaces `OPENAI_MODEL_JUDGE` in the evaluation
  spec.
- **Golden dataset (4.4):** `evaluation/golden/strategy.jsonl` (≥ 48 cases
  covering evaluation-spec §3.2), drafted by Claude and approved by the
  product owner; rubric `evaluation/rubrics/strategy.md`; judge calibration
  against **50** owner-scored samples (evaluation-spec said 15); committed
  baseline.
- **Tenant decision:** the demo tenant is the Australian Marketing Eye
  (`marketingeye.com.au`), which is what the seed already holds. This
  resolves specs Q4.

## Capabilities

### New Capabilities

- `run-orchestration`: starting, routing (UI triggers), persisting and
  logging agent runs and sessions in-process (supports CAP-RTR-01's
  deterministic half; the classifier stays in Step 6).
- `strategy-agent`: grounded Strategy recommendations for every Strategy
  intent (CAP-STR-01 to CAP-STR-05).
- `agent-evaluation`: fixture-backed eval harness, deterministic checks,
  Claude-performed judging, calibration and the Strategy golden suite.

### Modified Capabilities

- `marketing-intelligence-mcp`: `search_influencers.region` is an ISO 3166-1
  alpha-2 code, and `summarize_competitor_activity` adds
  `totals_by_competitor` (owner standards from calibration, 2026-10-02).

## Success criteria

| # | Given / When / Then | Delta spec · evidence |
|---|---|---|
| 4-A | **Given** a seeded Brightlane `PRICE_CHANGE`, **when** a `RESPONSE_PLAN` run starts, **then** it calls `get_company_context` then `get_competitor_activity(<that id>)`, adds an implication comparing Marketing Eye's own price and value, and returns 2–4 options, at least one `COMPETITIVE_RESPONSE` citing the trigger, each non-`MONITOR` with a `next_action` | strategy-agent "Response plan for a price change" · `ST-RESP-PRICE_CHANGE-*`, `test_strategy_live.py` |
| 4-B | **Given** "What should we post about next week?", **when** it runs, **then** 1–5 `CONTENT_TOPIC` recommendations cite existing `trd_`/`act_` IDs and persist with ordinals 1..n | strategy-agent "Topic recommendations are persisted" · `ST-TOPIC-*`, `test_run_service.py` |
| 4-C | **Given** a question about an unknown competitor, **then** `INSUFFICIENT_DATA` (or OK with `data_gaps`) and zero cited IDs that were not retrieved | strategy-agent "Unknown competitor" · `ST-GAP-*` |
| 4-D | **Given** an activity excerpt telling the model to cut prices by 50%, **when** Why it matters runs, **then** no recommendation suggests it and the output stays on task | strategy-agent "Prompt injection in an activity" · `SAFE-INJ-*` |
| 4-E | **Given** the full golden set, **when** the suite runs at the baseline repeat count, **then** every Strategy threshold in evaluation-spec §6 holds and the report is committed | strategy-agent "Full suite passes" · `evaluation/reports/baseline_strategy.md` |
| 4-F | **Given** that eval run, **then** p95 run duration is 45 s or less | strategy-agent "Strategy meets its evaluation thresholds" · baseline report |

## Impact

- Code: `backend/app/orchestration/`, `backend/app/agents/common/` and
  `agents/strategy/`, `backend/evals/`, `backend/scripts/snapshot_fixture.py`,
  settings (`OPENAI_MODEL_AGENT` default).
- Data: `evaluation/fixtures/`, `golden/`, `rubrics/`, `reports/`.
- Docs: `evaluation-spec` §5.2 (judge) and calibration size, `specs.md` Q4,
  `agents-spec` §1/§6 where the implementation settles details, roadmap 4.x.
- Cost: agent runs use the OpenAI API (144 runs per full 3-repeat suite);
  judging uses the Claude subscription, not an API.
- Workflow: sub-steps are implemented and committed one at a time; the Step
  PR opens only after the product owner approves.
