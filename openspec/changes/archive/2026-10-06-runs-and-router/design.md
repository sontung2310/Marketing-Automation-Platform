# Design

## Context

`RunService.start` (Step 4) routes, runs the agent and persists in one call. Events are collected in memory (`RunContext.events`) and written only at the end. Deterministic trigger routing exists (`routing.TRIGGER_ROUTES`), and chat requires an explicit agent. The API runs on Vercel as one Python function (Step 6 read side). The MCP runs only in docker-compose. The frontend (Step 7) already calls `/runs`, `/runs/{id}/events` and `/sessions/{id}`.

## Goals / Non-Goals

**Goals:**
- live agent runs on the Vercel site;
- chat routing per agents-spec §5.2;
- the router golden baseline.

**Non-Goals:**
- changes to agent code, instructions or skills;
- run cancellation;
- multi-tenant MCP;
- the Step 8 cost log and hardening.

## Decisions

1. **Prepare, then execute.** `prepare()` does the following, then returns `RunPlan(run, context, message)`:
   - routes the request (trigger, or the router for chat);
   - resolves the trigger or reference;
   - checks the daily cap;
   - opens the session;
   - writes the `RUNNING` run.

   `execute(plan)` runs the agent and persists everything, as `start` did. `start` stays as `prepare` plus `execute` for evals and tests, so their behaviour is unchanged.
2. **Events persist as they are emitted, without touching agent code.** `execute` runs a writer task that `$set`s `run.events` from `context.events` every 0.5 s and once more at the end. Agents keep emitting into the in-memory list exactly as before. This keeps `app/agents/` untouched, so the Strategy and Execution suites need no re-run. The SSE endpoint polls `runs.events` every 0.5 s from `Last-Event-ID`, and uses each event's `seq` as its ID. The stream ends on `run.completed` or `run.failed`, or closes after 55 s for serverless; the browser then resumes natively.
3. **Run after the 202 with FastAPI `BackgroundTasks`, verified on Vercel first.** Vercel's Python docs do not promise that work continues after the response. Task 1.1 is a spike on a preview deployment (reached with `vercel curl`): a background task writes to Mongo 40 s after the 202.
   - **If it survives:** use `BackgroundTasks`.
   - **If not, fallback:** the first `GET /runs/{id}/events` atomically claims the run (`execution_claimed_at` set only if absent) and runs it inside that streaming request, which stays open for the run's duration.

   **Spike result (task 1.1, 2026-10-06):** on a preview of the API project, `POST` returned `202` in 0.31 s, and the background task wrote its marker 40 s later. A streaming request whose client hung up after 5 s also finished its work. So runs execute through `BackgroundTasks`, and the fallback is not needed.

   Either way, a run left `RUNNING` past `RUN_WALL_CLOCK_S` (120 s) reads as `FAILED` with "The run was interrupted".
4. **The router is an orchestration service, not a third agent package.** `orchestration/router.py` holds `RouteDecision`, the router instructions (`router_instructions.md`) and a typed `classify()` (OpenAI Agents SDK, `output_type=RouteDecision`, `OPENAI_MODEL_ROUTER`). It never touches the MCP or Mongo. `decide()` turns a decision into a run, a clarification or an out-of-scope answer: the `INTENT_AGENT` registry maps each run intent to its agent, and three ordered rules cover the rest (out of scope always answers; without a hint, an unknown intent or confidence below 0.6 clarifies; a hint keeps its agent and falls back to that agent's default intent in `HINT_DEFAULT_INTENT`). `route_message()` resolves the decision's references before `decide()`, so an unresolvable "#7" answers "No recommendation #7 in this session" even when the model chose to clarify. The API and the router suite both route through it. `references.py` gains `resolve_reference()`, which turns `recommendation:N` or `deliverable:last` into the same trigger context as the matching UI button.
5. **The router suite reuses the harness.** It is a new entry in `evals/suites.py`, with deterministic checks only (no judge, no MCP, no fixture database beyond a session stub for `RT-REF`). Cases follow evaluation-spec §4 with a `route` expectation. A fresh reviewer subagent checks every case for over-fitting before the baseline (owner decision).
6. **The MCP lives in the API.** `app/api/main.py` mounts the existing MCP ASGI app at `/mcp`, in stateless HTTP mode, so each MCP call is self-contained across serverless invocations. On Vercel, `MCP_URL` points at `https://marketing-automation-api.vercel.app/mcp`: agents still reach it over HTTP, so the layering contract is unchanged. Compose keeps its separate `mcp` service.
7. **The daily cap is a count, not a counter document.** `prepare` counts the runs with `started_at` today (UTC; one company per deployment in the PoC) through the runs repository, using the existing index, and compares the count with `MAX_RUNS_PER_DAY` (default 50, where 0 disables runs). A small race at the boundary is acceptable for a demo. A chat message checks the cap before the router call, so a capped site spends nothing on models.
8. **The frontend run stream follows the activity stream fix.** Routine closes reconnect natively with `Last-Event-ID`. Only a stream the browser gives up on is reopened, after refetching the run. Restore uses `run.output` with its persisted IDs.

## Risks / Trade-offs

- [Vercel kills background work after the 202] → task 1.1 spike, then the claim fallback (Decision 3).
- [An MCP call to its own deployment adds an invocation per tool call] → acceptable for the PoC. A long-lived host can call the MCP in-process later.
- [The router model mislabels a demo message] → the golden `demo-path` cases must pass 100%, and low confidence clarifies instead of guessing.
- [Cost] → the daily cap, plus router calls on the small model only (`OPENAI_MODEL_ROUTER`, default `gpt-5.4-mini`).
- [`/mcp` is public, with no token] → accepted for the PoC (PR #40 review). Its tools are read-only and return the same demo data the public read endpoints already serve; the cost per call is one Mongo query. Add a bearer token shared with the agents before any real tenant data goes behind it.
- [A slow run read as interrupted] → `execute` stops its agent after 100 s, well inside the 120 s wall clock, and a run already read as interrupted is never overwritten.

## Migration Plan

1. The owner sets `MCP_URL` and `MAX_RUNS_PER_DAY` on the API project.
2. Merge, and production deploys.

Rollback: set `MAX_RUNS_PER_DAY=0`, and the site stays read-only.
