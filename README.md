# Marketing Automation Platform (PoC)

## 1. Introduction

**Goal.** Show a client, in one browser page and under five minutes, that a
platform can answer one question:

> "My competitor just did something. What does it mean for me, and can the
> platform do the work for me?"

It does this in three moves:

1. **Watch the market.** Competitor activity, tracked-keyword trends and
   relevant influencers come from an Intelligence DB that background pipelines
   keep filled.
2. **Decide.** The **Marketing Strategy Agent** answers "what should we do?"
   and grounds every recommendation in evidence it retrieved itself.
3. **Act.** The **Marketing Execution Agent** answers "do this task for me". It
   produces the deliverable (blog, social post, CEO post, email, ad copy,
   response brief) and proposes actions. The user approves an action and a mock
   connector "executes" it.

It is a proof of concept: single tenant (Marketing Eye), no authentication, and
all connectors are mock (nothing is really posted or emailed).

Full specification: [docs/specs.md](docs/specs.md). Code style:
[docs/coding-conventions.md](docs/coding-conventions.md). Structure and layering
rules: [AGENTS.md](AGENTS.md).

## 2. Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11/3.12, FastAPI, Pydantic, [uv](https://docs.astral.sh/uv/) |
| Agents | OpenAI Agents SDK (Strategy, Execution, plus a small Router model) |
| Agent data access | Marketing Intelligence MCP server (read-only tools over MongoDB) |
| Database | MongoDB (PyMongo); only `intelligence/repositories/` queries it at runtime |
| Frontend | React + Vite + Tailwind, design-system tokens only |
| Testing | pytest, Vitest, Playwright, Lighthouse |
| Quality gates | mypy (strict), ruff, import-linter (layering), ESLint, Prettier, OpenSpec |
| CI/CD | GitHub Actions (one **Check** job), Vercel Git integration |

Layering is enforced: `api → orchestration → agents → (MCP) → mcp_server →
intelligence.repositories → MongoDB`. Agents read data only through the MCP.

```text
backend/    FastAPI service, agents, MCP server, pipelines, evals
frontend/   React + Vite app (npm workspace)
evaluation/ golden datasets, fixtures, rubrics, reports
docs/       specs and contracts
openspec/   current specs and proposed changes
```

## 3. Installation

### 3.1 Prerequisites

Install these first and check the versions:

| Tool | Version | Check | Install |
|---|---|---|---|
| Node.js + npm | 22 or newer | `node -v` | https://nodejs.org or `nvm install 22` |
| Python | 3.11 or 3.12 (not 3.13) | `python3 --version` | uv can fetch it for you (below) |
| uv | latest | `uv --version` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` or `brew install uv` |
| Git | any | `git --version` | |
| MongoDB | a connection URI | | [MongoDB Atlas](https://www.mongodb.com/atlas) free cluster, or local (see below) |
| OpenAI API key | | | https://platform.openai.com/api-keys |
| Docker (optional) | any | `docker --version` | Only for the Docker run option and a local MongoDB |

### 3.2 Clone and install dependencies

Run everything from the repository root.

```bash
git clone <repository-url> Marketing-Automation
cd Marketing-Automation

npm ci                          # frontend + tooling deps; also installs the git pre-commit hook
uv sync --directory backend     # creates backend/.venv with the locked Python deps
```

If you have no suitable Python, run `uv python install 3.12` first; `uv sync`
then uses it automatically.

Only if you will run the browser tests (`npm run test:e2e`, `npm run check`):

```bash
npx playwright install chromium
```

### 3.3 Configure the environment

```bash
cp .env.example .env
```

Edit `.env` (it is git-ignored; never commit it). The backend reads the single
`.env` at the repository root.

| Variable | Required | What to put |
|---|---|---|
| `MONGODB_URI` | yes | Your Atlas connection string (copy the format from `.env.example`), or `mongodb://localhost:27017` for a local database |
| `MONGODB_DATABASE` | yes | Database the platform owns and writes to (default `marketing_automation`) |
| `OPENAI_API_KEY` | yes | Your OpenAI key |
| `OPENAI_MODEL_AGENT` | yes | Model for Strategy and Execution (default `gpt-5.5`) |
| `OPENAI_MODEL_ROUTER` | yes | Model for the request router (default `gpt-5.4-mini`) |
| `MCP_URL` | yes | Where the API finds the MCP server. Keep `http://localhost:8001/mcp` locally |
| `MCP_ALLOWED_HOSTS` | yes | Keep the default for local use |
| `DEFAULT_COMPANY_ID` | yes | Keep `cmp_marketing_eye` |
| `MAX_RUNS_PER_DAY` | yes | Agent runs allowed per UTC day (cost guard). `0` disables runs |
| `CORS_ORIGINS` | yes | Keep `["http://localhost:5173"]` locally |
| `COMPETITORSCOPE_DATABASE`, `DCT_DATABASE`, `PACE_DATABASE` | optional | Read-only source databases on the same cluster. The pipelines read them to fill the feed. Without access, the seeded data still lets the app run |
| `VITE_API_BASE_URL` | no | Leave empty locally (Vite proxies `/api` to :8000) |

**No MongoDB yet?** Start a throwaway local one and use
`MONGODB_URI=mongodb://localhost:27017`:

```bash
docker compose --profile test up -d mongo
```

If you use Atlas, add your IP address under Network Access first.

### 3.4 Seed the database

This loads the Marketing Eye company, competitors, keywords, influencers and
mock activity into `MONGODB_DATABASE`.

```bash
uv run --directory backend python scripts/seed_db.py --dry-run   # validate only, touches nothing
uv run --directory backend python scripts/seed_db.py             # write the seed data
```

## 4. Running the project

### 4.1 Quick look, no backend, no keys

Serves the whole UI from typed mock fixtures. Good for a first look.

```bash
npm run dev:web:fixtures
```

Open http://localhost:5173.

### 4.2 Full stack, three terminals

Needs the `.env` and seeded database from section 3. Run from the repository
root.

```bash
# Terminal 1: Marketing Intelligence MCP server (port 8001, must match MCP_URL)
uv run --directory backend uvicorn app.mcp_server.main:app --port 8001

# Terminal 2: Platform API (port 8000)
npm run dev:api

# Terminal 3: web UI (port 5173)
npm run dev:web
```

Then, once, in a fourth terminal, fill the feed with current data:

```bash
uv run --directory backend python scripts/run_pipelines.py
```

Open http://localhost:5173. Interactive API docs are at
http://localhost:8000/docs.

### 4.3 Full stack with Docker

```bash
docker compose up api mcp web
```

This starts the API (:8000), the MCP server (:8001) and the web UI (:5173), all
reading `.env`. Add `pipelines` to also refresh source data every 15 minutes.

### 4.4 Verify it works

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs   # API is up (expect 200)
uv run --directory backend python scripts/mcp_smoke.py   # MCP tools respond
```

Then in the UI: the competitor feed should list items; click one and run an
analysis or ask the chat for a deliverable.

### 4.5 Run the demo story

The 8-step demo is in [docs/specs.md §7](docs/specs.md#7-end-to-end-demo-story-acceptance-narrative).

1. Reset to a clean state. This **wipes** sessions, runs, recommendations,
   deliverables and actions in the database `.env` points at, then re-seeds.
   It prints which database it will wipe; without `--yes` it does nothing.

   ```bash
   uv run --directory backend python scripts/reset_demo.py --yes
   ```

2. Start the services (4.2 or 4.3) and run the pipelines once.
3. Play the story by hand at http://localhost:5173, or run it automated three
   times in a row. This spends real OpenAI budget:

   ```bash
   npm run demo:e2e
   ```

## 5. Development

Run `npm run check` before every PR. It is exactly what CI runs.

| Command | What it does |
|---|---|
| `npm run check` | Everything CI checks: typecheck, tests, lint, format, skills, API contract, OpenSpec, e2e, Lighthouse |
| `npm run typecheck` | mypy (strict) + `tsc` |
| `npm run test` | pytest unit tests + Vitest |
| `npm run test:integration` | pytest `-m integration` against `MONGODB_URI` (use the local `mongo` container) |
| `npm run test:e2e` | Playwright specs against the fixtures |
| `npm run lint` / `lint:fix` | ruff + import-linter + ESLint |
| `npm run format` / `format:check` | ruff format + Prettier |
| `npm run api:export` / `api:check` | Write `backend/openapi.json` / fail if it or `frontend/src/api/types.ts` is stale |
| `npm run openspec:check` | Validate OpenSpec changes and cross-change conflicts |
| `npm run build` | Frontend production build |

On commit, husky runs lint-staged, which fixes and formats staged files only.
Work happens on `feature/<step-number>-<slug>` branches; `main` is protected and
changes land through PRs. See [AGENTS.md](AGENTS.md) and
[docs/roadmap.md](docs/roadmap.md).

### Troubleshooting

| Symptom | Fix |
|---|---|
| `npm run dev:web` shows a wall of 502s | The API is not running. Start it (4.2) or use `npm run dev:web:fixtures` |
| `uv sync` complains about the Python version | Run `uv python install 3.12` |
| Settings validation error on start | A required `.env` variable is empty. Re-check section 3.3 |
| Mongo timeout / auth error | Check `MONGODB_URI`, and your IP in Atlas Network Access |
| Agent runs fail with a connection error | The MCP server is not running on :8001, or `MCP_URL` differs |
| Runs rejected after many tries | `MAX_RUNS_PER_DAY` reached; raise it in `.env` |
| `test:e2e` says a browser is missing | `npx playwright install chromium` |

## 6. CI/CD

- **CI** ([`ci.yml`](.github/workflows/ci.yml)): one **Check** job on pull
  requests to `main`, pushes to `main`, and manual runs. It runs
  `npm ci && uv sync --frozen`, then `npm run check`.
- **CD:** the Vercel Git integration, configured in
  [`vercel.json`](vercel.json). Every PR gets a preview deployment, and `main`
  deploys to production. No deploy workflow or GitHub secrets are needed.
- **Two Vercel projects** from the same repo:
  - **Web** (repo root): the static Vite build. `vercel.json` rewrites `/api/*`
    to the API project, so the browser stays same-origin.
  - **API** (Root Directory `backend`): FastAPI as a Python function from
    `backend/index.py`. It also serves the MCP at `/mcp` and runs agents in the
    background after a `202`. Set `MONGODB_URI`, `MONGODB_DATABASE`,
    `DEFAULT_COMPANY_ID`, `OPENAI_API_KEY`, `MCP_URL=https://<api-domain>/mcp`
    and `MAX_RUNS_PER_DAY` there (`OPENAI_MODEL_AGENT` and `OPENAI_MODEL_ROUTER`
    default to the values in `.env.example`). Allow Vercel's egress in MongoDB
    Atlas Network Access (`0.0.0.0/0`, or the Atlas Vercel integration). If the
    API domain is not `marketing-automation-api.vercel.app`, update the rewrite
    in `vercel.json`.
