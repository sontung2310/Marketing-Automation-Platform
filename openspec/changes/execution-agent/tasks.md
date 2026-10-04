# Tasks

Each numbered group is one roadmap sub-step, implemented, verified, committed
and pushed before the next begins. The Step PR opens only after the owner
approves.

## 1. 5.1 Execution agent

- [x] 1.1 Add `Company.spokesperson` (required) with a fictional Marketing Eye founder and CEO in the seed, and rename `ProposedAction.proposed_at` to `created_at`; verify seed validation fails without a spokesperson and `get_company_context` returns it in the MCP integration test.
- [x] 1.2 Move Strategy's run–validate–repair-once loop into `agents/common/repair.py` (design D1) and switch Strategy to it; verify every `tests/unit/test_strategy_*.py` and `test_run_mcp.py` pass unchanged.
- [x] 1.3 Add the deliverable-type registry (D2) and make trigger evidence IDs citable in the run service (D5); verify with unit tests that every `CREATE_SIMILAR` activity/channel pair, `FROM_RECOMMENDATION` and `INFLUENCER_OUTREACH` resolve, and that a recommendation trigger's evidence IDs join `retrieved_ids`.
- [x] 1.4 Add `ExecutionOutput` (agent-facing `ActionProposal`, D3), `agents/execution/instructions.md` rendered with the skill catalogue, the agent builder and `run_execution` on the shared loop, with grounding, type and status-shape problems; verify the instructions contain every agents-spec §2 and §7.3 element, and that unit tests over stubbed outputs repair once then fail with `UNGROUNDED_OUTPUT` or `INVALID_OUTPUT`.
- [x] 1.5 Add `persist_execution` (deliverable only at this point) to `PERSISTERS` and register the Execution agent; verify with an integration test against MongoDB that an `OK` run stores one deliverable linked to the run, its ID is in `output.final`, and a `NEEDS_CLARIFICATION` run stores nothing.

## 2. 5.2 Guards and repair

- [x] 2.1 Add `agents/execution/guards.py`: originality (12-word run, 5-gram Jaccard, short-source rule), the channel-limit registry, the competitor-name scan and `word_count` overwrite (D4); verify with unit tests covering each guard's pass and fail paths, including a 12-word copy and an 11-word near-copy.
- [ ] 2.2 Wire the guards into the repair loop with hard/soft severities: a hard failure after the repair fails the run (`UNORIGINAL_OUTPUT`), and a soft one becomes `FLAG` with a note; verify with stubbed-output unit tests that a copy is never returned and a surviving length breach reports `channel_fit: FLAG`.
- [ ] 2.3 Add `tests/integration/test_execution_live.py` (real MCP and OpenAI over the seeded database): `CREATE_SIMILAR` on a `NEW_BLOG` and on a LinkedIn `EXECUTIVE_POST`; verify the deliverable sides of 5-A and 5-B and save the run outputs as evidence.

## 3. 5.3 Proposed actions and mock connectors

- [ ] 3.1 Add the payload registry keyed by `ActionType` with the next-weekday 09:00 Australia/Sydney default (D3), and persist actions in `persist_execution` all-or-nothing (D6); verify with unit tests that a Friday maps to Monday 09:00 Sydney, a user-given `when` wins, and invalid payloads are rejected, and with an integration test that a failed action insert leaves no deliverable.
- [ ] 3.2 Add `connectors/base.py` (`Connector` protocol) and `connectors/mock/` (one connector per `ActionType`, mock receipts) in an enum-keyed registry; verify each returns its agents-spec §8 receipt shape.
- [ ] 3.3 Add the repository `transition` and `orchestration/actions.py` (`ActionService` approve/discard with the state machine, D7); verify with unit tests that only `PROPOSED` transitions and that a connector error yields `FAILED`.
- [ ] 3.4 Add `api/routes/actions.py` (`POST /actions/{id}/approve` with `payload_overrides`, `POST /actions/{id}/discard`); verify `tests/integration/test_actions.py` against MongoDB over HTTP covers 5-D: approve → `EXECUTED` with a receipt, a second approve → `409`, a discarded action → `409`, an unknown ID → `404`, and a bad override → `422`.
- [ ] 3.5 Re-run the live test with actions; verify 5-A proposes `create_cms_draft` and 5-B proposes `schedule_social_post` for the next weekday at 09:00 Sydney, and save the evidence.

## 4. 5.4 Golden dataset, calibration and baseline

- [ ] 4.1 Extend the harness for the `execution` suite (D9): suite registries, `seed_history` per output model, the Execution checks (`deliverable_shape`, `originality`, `competitor_naming`, `proposed_actions_any`) and judge dimensions; add the fixture's Execution records and re-snapshot it with the spokesperson; verify with unit tests for each new check's pass and fail paths, and a 3-case run through `tests/integration/test_eval_runner.py`.
- [ ] 4.2 Draft `evaluation/golden/execution.jsonl` (≥ 48 cases meeting every evaluation-spec §3.3 minimum, ≤ 30% upstream-mined, `demo-path` tags) and `evaluation/rubrics/execution.md`; run a fresh-subagent over-fitting review; verify the loader accepts the file and the category counts meet §3.3.
- [ ] 4.3 **Owner approval:** the owner reviews and approves the golden file and rubric; apply requested changes.
- [ ] 4.4 Run the suite with `--repeats 1`, judge it, and generate the 50-sample calibration sheet; **the owner scores it**; verify agreement within ±1 is at least 80% and record it in the rubric.
- [ ] 4.5 Run the full suite with `--repeats 1`, judge it, and fix agent behaviour until every evaluation-spec §6 Execution threshold holds (5-C, 5-E, 5-F, p95 ≤ 60 s); commit `evaluation/reports/baseline_execution.json` and its Markdown copy.

## 5. Documentation and close-out

- [ ] 5.1 Update `agents-spec` §7.2–§8 (the `ActionProposal` shape, guard severities and code-built payloads), `data-contract` (company `spokesperson`, action `created_at`), `api-contract` (the action endpoints and their `404`/`409`/`422`), `evaluation-spec` (Execution checks, short-source rule) and roadmap: move 5-C's "#7" half to 6.4/`RT-REF`, add the action endpoints to 5.3, and tick 5.1–5.4 with evidence; verify the docs match the code.
- [ ] 5.2 Re-run the Strategy suite with `--repeats 1` after the D1 refactor and the fixture re-snapshot; verify every evaluation-spec §6 Strategy threshold still holds, and attach the report.
- [ ] 5.3 Run `npm run check` and `npm run test:integration`; verify both are green.
- [ ] 5.4 Ask the owner to approve opening the Step PR; then open it with the eval report summaries and 5-A–5-F evidence, and run the fair review.
