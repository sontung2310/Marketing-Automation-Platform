# Tasks

Each numbered group is one roadmap sub-step, implemented, verified, committed
and pushed before the next begins. The Step PR opens only after the owner
approves.

## 1. 4.1 Run service

- [ ] 1.1 Verify the OpenAI key can call `gpt-5.6-luna` with structured output and set it as the `OPENAI_MODEL_AGENT` default; stop for the owner if the call fails.
- [ ] 1.2 Add the trigger routing registry (agents-spec §5.1) and `EXPLICIT` chat route; verify with a unit test that every `(kind, action)` pair maps and an unknown pair is rejected.
- [ ] 1.3 Add `RunContext`, reference resolution through repositories (company-scoped) and session creation; verify an unknown `ref_id` is rejected with no run persisted.
- [ ] 1.4 Add the run service with the event log (`run.started` … `run.completed`/`run.failed`, increasing `seq`) and run persistence, using a stub agent; verify with an integration test against MongoDB that a completed and a failed run persist the scenarios' fields.

## 2. 4.2 Strategy agent

- [ ] 2.1 Add the counting MCP wrapper (12-call limit, tool-call records, `agent.tool` events, retrieved-ID set); verify with unit tests over a fake MCP session.
- [ ] 2.2 Add `StrategyOutput`, `agents/strategy/instructions.md` rendered with the skill catalogue, and the agent builder (MCP, `load_skill`, `max_turns=16`); verify the instructions contain every agents-spec §2 element.
- [ ] 2.3 Add post-validation (grounding repair once, `UNGROUNDED_OUTPUT`, ordinal renumbering, `next_action` rule) and recommendation persistence; verify with unit tests that stub the model output.
- [ ] 2.4 Run the price-change response plan and "What should we post about next week?" against the seeded database, real MCP and real OpenAI; verify scenarios 4-A and 4-B and save the run output as evidence.

## 3. 4.3 Eval harness and fixture

- [ ] 3.1 Add `scripts/snapshot_fixture.py` and `evaluation/fixtures/intelligence_v1.json` with the adversarial records (injection, stale, unknown-competitor gaps); verify the fixture loads and every `*_fx_*` ID is present.
- [ ] 3.2 Add the case loader (evaluation-spec §4 schema, fixture-ID validation) and the throwaway-database + in-process MCP runner; verify a case with a missing fixture ID fails at load time.
- [ ] 3.3 Add the deterministic checks (evaluation-spec §5.1, Strategy-applicable) with unit tests for each check's pass and fail path.
- [ ] 3.4 Add judge bundles, the score schema, `evals.cli report` and `evals.cli calibrate`; verify a report with missing scores is marked incomplete and cannot be written as a baseline.
- [ ] 3.5 Add the `.agents/skills/eval-judge/` team skill (with its `.claude/skills/` symlink and `skills-lock.json` entry); verify by judging a 3-case run in session and building its report.

## 4. 4.4 Golden dataset, calibration and baseline

- [ ] 4.1 Draft `evaluation/golden/strategy.jsonl` (≥ 48 cases meeting every evaluation-spec §3.2 minimum, ≤ 30% upstream-mined, `demo-path` tags) and `evaluation/rubrics/strategy.md`; run a fresh-subagent over-fitting review; verify the loader accepts the file and the category counts meet §3.2.
- [ ] 4.2 **Owner approval:** the owner reviews and approves the golden file and rubric; apply requested changes.
- [ ] 4.3 Run the suite with `--repeats 1`, judge it, and generate the 50-sample calibration sheet; **the owner scores it**; verify agreement within ±1 is at least 80% and record it in the rubric.
- [ ] 4.4 Run the full suite with `--repeats 3`, judge it, and fix agent behaviour until every evaluation-spec §6 Strategy threshold holds (4-C, 4-D, 4-E, 4-F); commit `evaluation/reports/baseline_strategy.json`.

## 5. Documentation and close-out

- [ ] 5.1 Update `evaluation-spec` §5.2 (Claude judge, bundles, skill) and the calibration size (50), `specs.md` Q4 (Australian Marketing Eye), `agents-spec` §1/§6 details settled in implementation, `data-contract` if run fields change, and tick roadmap 4.1–4.4 with evidence; verify the docs match the code.
- [ ] 5.2 Run `npm run check` and `npm run test:integration`; verify both are green.
- [ ] 5.3 Ask the owner to approve opening the Step PR; then open it with the eval report summary and 4-A–4-F evidence, and run the fair review.
