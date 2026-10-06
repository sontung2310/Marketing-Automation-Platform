# Proposal: agent runs over HTTP and the chat router (rest of Step 6)

Roadmap: 6.2, 6.4, 6.5 · CAP-RTR-01, CAP-UI-02

## Why

Steps 4 and 5 built the Strategy and Execution agents, but they only run in-process and in evals. The live site's chat, **Plan a response**, **Why it matters**, **Do this** and **Approve** all call `/api/runs` and `/api/sessions`, which don't exist yet. This change finishes Step 6, so the first website can run the agents end to end.

## What Changes

- **6.2 runs over HTTP:**
  - `POST /api/runs` returns `202` with the RUNNING run, or `200` with a router answer and no run.
  - `GET /api/runs/{id}/events` is the SSE stream. Events are persisted as they are emitted, so the stream is live, and a reconnect replays from `Last-Event-ID`.
  - `GET /api/runs/{id}` and `GET /api/sessions/{id}`. A restored session carries each run's persisted IDs, so restored cards can still approve.
  - `RunService.start` splits into `prepare` and `execute`.
  - The frontend run stream reconnects with `Last-Event-ID` instead of ending the run on error.
- **6.4 chat router:** a classifier (`RouteDecision`, `OPENAI_MODEL_ROUTER`) handles chat messages, with these paths:
  - `agent_hint` validation;
  - clarify, when confidence is below 0.6;
  - a fixed out-of-scope answer;
  - session references (`recommendation:N`, `deliverable:last`). An unresolvable reference clarifies with "No recommendation #N in this session".
- **6.5:** the router golden dataset `evaluation/golden/router.jsonl` (≥ 36 cases, evaluation-spec §3.1), a `router` suite in the harness, and the committed baseline.
- **Hosting (owner decision):** the Marketing Intelligence MCP is mounted at `/mcp` inside the API project, so agent runs work on Vercel.
- **Cost guard (owner decision):** `MAX_RUNS_PER_DAY` caps the agent runs started per UTC day. Past the cap, `POST /runs` returns `429 RATE_LIMITED` with a clear message.

## Capabilities

### New Capabilities
- `run-api`: runs, the run event stream, run and session reads, and the daily run cap over HTTP.
- `chat-router`: classifier routing of chat messages, hints, clarification, out-of-scope answers and session references.

### Modified Capabilities
- (none) `run-orchestration` keeps its behaviour. Prepare and execute is an internal split of the same start.

## Impact

- **Backend:**
  - `app/orchestration/` (`run_service`, a new `router`, `references`, an event writer);
  - `app/api/routes/runs.py`;
  - `app/api/main.py` (mounts `/mcp`);
  - `app/core/config.py` (`max_runs_per_day`);
  - `backend/evals/` (router suite).
- **Agents:** no change to agent code, instructions or skills. The router is a new orchestration-level classifier.
- **Frontend:** `useWorkspace` run stream reconnect, session restore with persisted IDs, and the rate-limit message.
- **Ops:** the API project needs `MCP_URL=https://marketing-automation-api.vercel.app/mcp` and `MAX_RUNS_PER_DAY` (owner sets both). The MCP host allowlist gains the API domain.
- **Docs:** api-contract (`429 RATE_LIMITED`, run stream close and resume, the session payload), agents-spec §5 (router details), README and roadmap.
