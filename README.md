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

| Command | What it does |
|---|---|
| `npm run dev:api` / `npm run dev:web` | FastAPI on :8000 / Vite on :5173 |
| `npm run dev:web:fixtures` | Vite on :5173 with the Platform API served from the typed MSW fixtures |
| `npm run check` | Everything CI checks: `typecheck`, `test`, `lint`, `format:check`, `openspec:check`, `test:e2e` |
| `npm run typecheck` | mypy (strict) + `tsc` |
| `npm run test` | pytest unit tests + Vitest |
| `npm run test:integration` | pytest `-m integration` against `MONGODB_URI` |
| `npm run lint` / `lint:fix` | ruff + import-linter layering contracts + ESLint |
| `npm run format` / `format:check` | ruff format + Prettier |
| `npm run openspec:check` | `openspec validate --all --strict` + the cross-change conflict check |
| `npm run test:e2e` | Playwright specs for the workspace, against the fixtures |
| `npm run build` | Frontend production build |

On commit, husky runs lint-staged, which fixes and formats **staged files
only** (ruff for Python; ESLint and Prettier for the frontend).

### Running the workspace without a backend

The Platform API arrives in roadmap Step 6, so `npm run dev:web` alone shows a
wall of 502s. Use `npm run dev:web:fixtures`, which sets `VITE_USE_FIXTURES=1`
and serves every documented endpoint from the typed MSW handlers in
`frontend/src/test/fixtures/`. The same handlers back Vitest and Playwright, so
what you click is what CI checks. The flag is read only in a dev build; a
production build never imports the worker.

## CI/CD

- **CI** ([`ci.yml`](.github/workflows/ci.yml)): one **Check** job on pull
  requests to `main`, pushes to `main`, and manual runs. It installs the
  dependencies (`npm ci && uv sync --frozen`) and runs `npm run check`.
- **CD:** the Vercel Git integration, configured in
  [`vercel.json`](vercel.json). Every PR gets a preview deployment, and
  `main` deploys to production. Connect the repo once in the Vercel
  dashboard; no deploy workflow or GitHub secrets are needed.

## Repository layout

The layout is described in [AGENTS.md §1](AGENTS.md#1-project-structure).
