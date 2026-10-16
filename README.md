# Marketing Automation Platform (PoC)

Two agents working over a shared Marketing Intelligence layer. The
**Marketing Strategy Agent** decides what the business should do. The
**Marketing Execution Agent** produces the deliverables and proposes actions.
The spec starts at [docs/specs.md](docs/specs.md). Code style is in
[docs/coding-conventions.md](docs/coding-conventions.md), and structure and
layering rules are in [AGENTS.md](AGENTS.md).

## Prerequisites

- Node 22+ and npm
- Python 3.11 and [uv](https://docs.astral.sh/uv/)
- A MongoDB URI and an OpenAI API key

## Setup

```bash
cp .env.example .env   # fill in MONGODB_URI, OPENAI_API_KEY and the model names
npm ci                 # frontend and tooling deps; also installs the husky pre-commit hook
uv sync --directory backend   # Python env for the backend service
```

## Scripts

| Command                               | What it does                                                                                                                 |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `npm run dev:api` / `npm run dev:web` | FastAPI on :8000 / Vite on :5173                                                                                             |
| `npm run dev:web:fixtures`            | Vite on :5173 with the Platform API served from the typed MSW fixtures                                                       |
| `npm run check`                       | Everything CI checks: `typecheck`, `test`, `lint`, `format:check`, `skills:check`, `api:check`, `openspec:check`, `test:e2e`, `lighthouse` |
| `npm run typecheck`                   | mypy (strict) + `tsc`                                                                                                        |
| `npm run test`                        | pytest unit tests + Vitest                                                                                                   |
| `npm run test:integration`            | pytest `-m integration` against `MONGODB_URI`                                                                                |
| `npm run lint` / `lint:fix`           | ruff + import-linter layering contracts + ESLint                                                                             |
| `npm run format` / `format:check`     | ruff format + Prettier                                                                                                       |
| `npm run api:export` / `api:check`    | Write `backend/openapi.json` / fail when it is stale or `frontend/src/api/types.ts` drifts from it                           |
| `npm run openspec:check`              | `openspec validate --all --strict` + the cross-change conflict check                                                         |
| `npm run test:e2e`                    | Playwright specs for the workspace, against the fixtures                                                                     |
| `npm run demo:e2e`                    | The demo story (`frontend/e2e/demo.spec.ts`) against a real, running backend and real OpenAI - see "Running the demo" below  |
| `npm run build`                       | Frontend production build                                                                                                    |

On commit, husky runs lint-staged, which fixes and formats **staged files
only** (ruff for Python; ESLint and Prettier for the frontend).

### Running the workspace without a backend

The read side of the Platform API (company, feed, insights, simulate) is live
from roadmap Step 6; run and session routes follow Steps 4–5. Without a running
API, `npm run dev:web` alone shows a wall of 502s. Use `npm run dev:web:fixtures`, which sets `VITE_USE_FIXTURES=1`
and serves every documented endpoint from the typed MSW handlers in
`frontend/src/test/fixtures/`. The same handlers back Vitest and Playwright, so
what you click is what CI checks. The flag is read only in a dev build; a
production build never imports the worker.

### Running the demo

The 8-step demo story is in [docs/specs.md §7](docs/specs.md#7-end-to-end-demo-story-acceptance-narrative);
it is also the Playwright test `frontend/e2e/demo.spec.ts`.

1. **Reset to a clean state.** From the repository root, with `.env` pointed
   at the database you want to demo from (never the shared production
   database by accident - the command prints which one it is about to wipe):

   ```bash
   uv run --directory backend python scripts/reset_demo.py --yes
   ```

   This deletes every session, run, recommendation, deliverable, action and
   simulated activity for the default company, then re-seeds it from
   `backend/app/pipelines/seed/`. Without `--yes` it does nothing and reports
   which database it would have wiped.

2. **Start the services.** Either `docker compose up api mcp web` (see
   `docker-compose.yml`), or three terminals: `npm run dev:api`,
   `uv run --directory backend uvicorn app.mcp_server.main:app --port 8001`
   (matching `MCP_URL` in `.env`), and `npm run dev:web`.
3. **Run the pipelines once** so the feed has current data:
   `uv run --directory backend python scripts/run_pipelines.py`.
4. **Play the story** by hand at `http://localhost:5173`, following specs.md
   §7 step by step, or run it automated and three times in a row (roadmap
   8-A), which needs a real `OPENAI_API_KEY` and spends real OpenAI budget:

   ```bash
   npm run demo:e2e
   ```

   The same test also runs on demand in CI
   ([`demo-e2e.yml`](.github/workflows/demo-e2e.yml), `workflow_dispatch`
   only) against a scratch database, never the shared one.

## CI/CD

- **CI** ([`ci.yml`](.github/workflows/ci.yml)): one **Check** job on pull
  requests to `main`, pushes to `main`, and manual runs. It installs the
  dependencies (`npm ci && uv sync --frozen`) and runs `npm run check`.
- **CD:** the Vercel Git integration, configured in
  [`vercel.json`](vercel.json). Every PR gets a preview deployment, and
  `main` deploys to production. Connect the repo once in the Vercel
  dashboard; no deploy workflow or GitHub secrets are needed.
- **Two Vercel projects** from the same repo:
  - **Web** (repo root): the static Vite build. `vercel.json` rewrites
    `/api/*` to the API project, so the browser stays same-origin.
  - **API** (Root Directory `backend`): FastAPI as a Python function, from
    `backend/index.py`; `backend/vercel.json` pins the FastAPI framework so the
    project is never built as a static site. It also serves the Marketing
    Intelligence MCP at `/mcp`, and runs agents in the background after `202`.
    Set `MONGODB_URI`, `MONGODB_DATABASE`, `DEFAULT_COMPANY_ID`, `OPENAI_API_KEY`,
    `MCP_URL=https://marketing-automation-api.vercel.app/mcp` and
    `MAX_RUNS_PER_DAY` (the daily cost guard) there (`OPENAI_MODEL_AGENT` and
    `OPENAI_MODEL_ROUTER` are optional and default to the models in `.env.example`), and allow Vercel's
    dynamic egress in MongoDB Atlas Network Access (`0.0.0.0/0`, or the Atlas
    Vercel integration). If the API project's domain is not
    `marketing-automation-api.vercel.app`, update the rewrite in `vercel.json`.

## Repository layout

The layout is described in [AGENTS.md §1](AGENTS.md#1-project-structure).
