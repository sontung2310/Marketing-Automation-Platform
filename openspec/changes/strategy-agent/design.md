# Design

## Context

See proposal.md for why. The data models and repositories for `sessions`,
`runs` and `recommendations` exist (Step 1); the MCP server runs over HTTP
(Step 2); `load_skill`, allowlists and `render_catalogue` exist (Step 3).
`app/orchestration/`, `app/agents/strategy/` and `backend/evals/` are empty
shells. Import-linter already enforces `api → orchestration → agents` and
forbids agents from touching repositories. The seed already holds the
Australian Marketing Eye.

## Goals / Non-Goals

**Goals:**

- One run path that Step 5 (Execution) and Step 6 (HTTP/SSE) reuse unchanged.
- Grounding enforced in code, not trusted to the prompt.
- An eval loop cheap enough to run often: OpenAI only for agent runs,
  Claude subscription for judging.

**Non-Goals:**

- HTTP endpoints, SSE streaming, the chat classifier (Step 6).
- The Execution agent, guards and connectors (Step 5).
- Running judged evals in CI.

## Decisions

1. **Run service owns persistence; agents stay pure.** `orchestration/`
   routes the trigger, resolves `ref_id` through repositories, builds the
   `RunContext`, runs the agent and persists the run, events and
   recommendations. The agent package only builds an SDK `Agent` and
   validates its output, so it keeps no database access (import-linter).
   Alternative rejected: agents persisting their own output, which breaks the
   layering and duplicates work in Step 5.

2. **Deterministic routing is a registry.** A `dict[(TriggerKind, Action)] →
   (AgentName, intent)` built from agents-spec §5.1, with an exhaustiveness
   test. Chat runs in Step 4 require an explicit agent and record route
   method `EXPLICIT` with intent `CHAT`; the Step 6 classifier fills the real
   intent later. Alternative rejected: an if/else chain per trigger.

3. **Tool accounting in one MCP wrapper.** The agent gets the MCP server
   through a thin subclass of the SDK's `MCPServerStreamableHttp` whose
   `call_tool` enforces the 12-call limit (returning `LIMIT_REACHED`),
   records the call (name, args summary, duration, result count), emits an
   `agent.tool` event, and collects every returned record ID into the run's
   retrieved-ID set. Alternatives rejected: SDK run hooks (they cannot
   short-circuit a call) and parsing IDs from the transcript afterwards.

4. **Grounding repair is one extra turn.** After the SDK parses
   `StrategyOutput`, code compares cited IDs with the retrieved set. Unknown
   IDs trigger one follow-up run with the same conversation and the message
   "these IDs were not retrieved: …"; a second failure marks the run
   `FAILED/UNGROUNDED_OUTPUT`. Ordinals are renumbered 1..n in code rather
   than re-prompted, because order is already meaningful.

5. **Model from settings.** `OPENAI_MODEL_AGENT` defaults to
   `gpt-5.6-luna`; the first task verifies that the key can call it and
   stops for the owner if not.

6. **Eval fixture and isolation.** `scripts/snapshot_fixture.py` exports the
   owned collections plus hand-written adversarial records (`act_fx_…`,
   `trd_fx_…`, `inf_fx_…`, including the injection and stale cases) to
   `evaluation/fixtures/intelligence_v1.json`. The harness loads it into
   `marketing_automation_eval_<run>` on the compose `mongo:7` service, starts
   the MCP app in-process on a free port against that database, and drops
   the database afterwards.

7. **Claude judge through files and a team skill.** `evals.cli run` writes
   `evaluation/reports/<run_id>/runs.jsonl` and one judge bundle per
   schema-valid run. A team skill, `.agents/skills/eval-judge/`, tells Claude
   Code how to spawn fresh subagents that each score a batch of bundles
   against `rubrics/<suite>.md` and write `scores.jsonl`, with no access to
   other scores. `evals.cli report <run_id>` validates the scores with a
   Pydantic schema, merges them and applies §6 thresholds; missing scores
   mark judging incomplete. Alternatives rejected: an OpenAI judge (API cost
   the owner declined) and calling Claude from Python (it would need a paid
   API key).

8. **Calibration as a scoring sheet.** `evals.cli calibrate <run_id>` samples
   50 schema-valid runs across categories into a Markdown sheet for the owner
   to score, then computes ±1 agreement against the Claude scores and appends
   the result to the rubric file.

9. **Golden cases are drafted, reviewed, then approved.** Claude drafts
   `strategy.jsonl` against the fixture, a fresh subagent reviews each
   `expect` block for over-fitting (evaluation-spec §7), and the owner
   approves the file before any baseline run.

## Risks / Trade-offs

- **[Claude judging cannot fix temperature]** → anchored rubric examples,
  batch-independent subagents and the 50-sample calibration gate.
- **[Judged runs are manual]** → deterministic checks carry the regression
  gate; judging runs before baselines and prompt/model changes.
- **[`gpt-5.6-luna` unavailable or slow]** → checked in task 1.1; latency is
  measured against the 45 s p95 target in every report.
- **[OpenAI cost of eval runs]** → develop with `--repeats 1` and
  `--cases`, use 3 repeats only for the baseline.
- **[Fixture drift from the seed]** → fixture is versioned; cases pin
  `intelligence_v1`.

## Migration Plan

No data migration. New collections' documents are written by the run
service only. Rollback removes the new modules; Steps 0–3 behaviour is
unchanged.
