# Marketing Automation Platform (PoC)

Two agents working over a shared Marketing Intelligence layer. The
**Marketing Strategy Agent** decides what the business should do. The
**Marketing Execution Agent** produces the deliverables and proposes actions.
The spec starts at [docs/specs.md](docs/specs.md). Code style is in
[docs/coding-conventions.md](docs/coding-conventions.md), and structure and
layering rules are in [AGENTS.md](AGENTS.md).

## Prerequisites

- Python 3.11 and [uv](https://docs.astral.sh/uv/)
- Node 22 and pnpm 9 (`corepack enable`)
- Docker (for the local stack and integration tests)
- A MongoDB URI and an OpenAI API key

## Setup

```bash
cp .env.example .env              # fill in MONGODB_URI, OPENAI_API_KEY, model names
uv sync                           # Python env (backend, tests, evals, scripts)
(cd frontend && pnpm install)    # frontend deps
uv run pre-commit install         # git hooks
```

## Run locally

```bash
make api          # FastAPI on :8000   (GET /api/health)
make web          # Vite on :5173
# or everything in containers:
docker compose up --build
```

## Quality checks

`make check` runs the same gates as CI.

| Command | What it runs |
|---|---|
| `make backend-check` | ruff format check, ruff lint, mypy (strict), import-linter layering contracts, pytest unit tests |
| `make frontend-check` | ESLint (design tokens only, no Tailwind arbitrary values), Prettier, `tsc`, Vitest, production build |
| `make openspec-check` | `openspec validate --all --strict`, plus the cross-change conflict and roadmap-reference check |
| `make integration` | pytest `-m integration` against `MONGODB_URI` |

## CI/CD

| Workflow | Trigger | Jobs |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | PRs and pushes to `main` | backend · frontend · openspec · repo hygiene (conflict markers, mergeability with base, contract-doc drift, secret scan) · PR conventions (branch name, Conventional Commit title) |
| [`cd.yml`](.github/workflows/cd.yml) | CI succeeded | Frontend → Vercel (a preview per PR, production from `main`) · backend image → GHCR (from `main`) |

Required repository secrets for CD: `VERCEL_TOKEN`, `VERCEL_ORG_ID` and
`VERCEL_PROJECT_ID`. Until they are set, the Vercel jobs skip with a notice.

## Repository layout

The layout is described in [AGENTS.md §1](AGENTS.md#1-project-structure).
