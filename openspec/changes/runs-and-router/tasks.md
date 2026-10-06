# Tasks

## 1. 6.2 Runs over HTTP

- [ ] 1.1 Spike: on a Vercel preview reached with `vercel curl`, check whether a FastAPI background task survives 40 s after a `202` (it writes a marker to a throwaway database). Record the result in design.md and pick Decision 3's path.
- [ ] 1.2 Split `RunService` into `prepare` and `execute`, with the live event writer (0.5 s) and the wall-clock interrupted rule. Keep `start` as a wrapper. Verify the existing run-orchestration tests still pass, plus a new test proving events are readable from Mongo before the run ends.
- [ ] 1.3 Add `POST /runs`, `GET /runs/{id}`, `GET /runs/{id}/events` (SSE, `seq` IDs, replay, 55 s close) and `GET /sessions/{id}`, with `run.output` holding the `output.final` payload. Verify integration tests for 6-C (202 within 500 ms, ordered events), 6-D (replay after `seq` 3), 422 and 404, and the restored-approve scenario.
- [ ] 1.4 Add the daily run cap (`MAX_RUNS_PER_DAY`, `429 RATE_LIMITED`); verify the cap scenario.
- [ ] 1.5 Mount the MCP at `/mcp` in the API app, stateless. Verify that a run on the local API with `MCP_URL` pointing at its own `/mcp` completes, and that `/health` reports `mcp: ok`.
- [ ] 1.6 Frontend: the run stream reconnects natively with `Last-Event-ID`, is reopened only after the browser gives up, restores from `run.output` with persisted IDs, and shows the rate-limit message. Verify hook and component tests and the Playwright run specs.

## 2. 6.4 Chat router

- [ ] 2.1 Add `orchestration/router.py` (`RouteDecision`, `router_instructions.md`, `classify()` on `OPENAI_MODEL_ROUTER`) and the decision-outcome registry (run, clarify, out of scope). Verify unit tests with a stubbed classifier for every outcome, the 0.6 confidence rule and hint handling.
- [ ] 2.2 Add `resolve_reference()` for `recommendation:N` and `deliverable:last`, with the "No recommendation #N in this session" clarification. Verify unit and integration tests for the 5-C scenarios.
- [ ] 2.3 Wire the router into `prepare` for chat. Verify 6-E against the real router model.

## 3. 6.5 Router golden dataset

- [ ] 3.1 Add the `router` suite to the eval harness (deterministic checks, report, baseline gating); verify unit tests.
- [ ] 3.2 Write `evaluation/golden/router.jsonl` (≥ 36 cases, every §3.1 category at its minimum, `demo-path` tags). A fresh reviewer subagent checks it for over-fitting; verify `parse_cases` loads it.
- [ ] 3.3 Run `python -m evals.cli run --suite router --repeats 1` and commit `baseline_router.json` and `.md`; verify every §6 router threshold holds (6-F).

## 4. Hosting, docs and close

- [ ] 4.1 The owner sets `MCP_URL=https://marketing-automation-api.vercel.app/mcp` and `MAX_RUNS_PER_DAY` on the API project. Verify on the live site: **Plan a response** on a `PRICE_CHANGE` streams to Strategy recommendations, **Do this** produces a deliverable, and **Approve** executes (screenshots in the PR).
- [ ] 4.2 Update api-contract (`429 RATE_LIMITED`, run stream close and resume, session payload, `/mcp` on the API), agents-spec §5 (router module, fixed messages), README (Vercel env) and roadmap; verify the docs match the code.
- [ ] 4.3 Run `npm run check`, `npm run test:integration` and the router suite. The Strategy and Execution suites are not re-run, because no agent code, instructions, skills or MCP tools change (the MCP is only mounted). Record that in the PR.
