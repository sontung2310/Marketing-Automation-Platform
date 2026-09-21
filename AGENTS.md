# AGENTS.md: Marketing Automation Platform (PoC)

A Strategy agent decides what to do, and an Execution agent produces the
deliverables. Both read a Marketing Intelligence MCP over MongoDB, behind a
one-page React UI. Start with [docs/specs.md](docs/specs.md).

## Read first

| Before you… | Read |
|---|---|
| write any code | [docs/coding-conventions.md](docs/coding-conventions.md) (binding) |
| touch data, the API, agents or the UI | [data-contract](docs/data-contract.md) · [api-contract](docs/api-contract.md) · [agents-spec](docs/agents-spec.md) · [ui-spec](docs/ui-spec.md) |
| pick up work | the GitHub issue, [docs/roadmap.md](docs/roadmap.md) and the relevant `openspec/specs/` |
| change agent behaviour | [docs/evaluation-spec.md](docs/evaluation-spec.md) |
| start or resume a lead/implementer loop | [docs/agents/collaboration.md](docs/agents/collaboration.md) |

## 1. Project structure

Update this section before adding a top-level folder or a backend module.

```text
backend/                 Python service: pyproject.toml, uv.lock, Dockerfile (build context)
  app/                   the `app` package
    core/                settings, Mongo client, logging, domain errors
    intelligence/        domain models + repositories/ (the only runtime Mongo queries)
    pipelines/           sources/ (read-only adapters), seed/ → owned collections
    mcp_server/          Marketing Intelligence MCP: read-only tools for the agents
    skills/              skill loader + library/ (vendored product marketing skills)
    agents/              common/, strategy/, execution/ (OpenAI Agents SDK)
    orchestration/       routing, runs, sessions
    connectors/          action connectors (mock/ in the PoC)
    api/                 FastAPI routes and schemas
  tests/                 unit/, integration/
  evals/                 golden datasets, fixtures, runner, reports
  scripts/               seed, pipeline and fixture CLIs
frontend/                React + Vite service (npm workspace)
  src/                   api/ (sole backend caller), components/ds/, features/, hooks/, lib/, styles/theme.css (sole token source)
tools/                   repo tooling in Node (OpenSpec conflict check)
docs/  openspec/         specs and plan; specs/ (current behaviour), changes/ (proposed)
.agents/skills/          team skills (source of truth); .claude/skills/ links to them
```

Each service is self-contained, with its own dependencies and build. The
root holds only shared tooling: `package.json` (the task runner and npm
workspace), `vercel.json`, `docker-compose.yml`, `.github/` and the shared
`.env`.

## 2. Code rules

Layering is enforced by import-linter:
`api → orchestration → agents → (MCP) → mcp_server → intelligence.repositories → MongoDB`.

- **MongoDB access:** only `intelligence/repositories/` and
  `pipelines/sources/` query MongoDB, and sources only read.
- **Agents:**
  - read data only through the Intelligence MCP;
  - stay independent of each other;
  - return proposed actions, which `connectors/` execute after user
    approval.
- **API routes** validate and delegate. Business logic lives in services.
- **Frontend:** only `src/api/` calls the backend.
- **Style** (binding, from the conventions doc):
  - Python + FastAPI + OpenAI Agents SDK on the backend.
  - React + Vite + Tailwind on the frontend, with design-system tokens only.
  - Reuse existing code, and use one pattern per kind of problem.
  - Handle types through registries keyed by enums rather than branches.
  - Make each change as simple as the problem allows.
- **MongoDB MCP in `.mcp.json`:** a read-only inspection tool for
  developers, outside the runtime path. The platform's own MCP is
  `mcp_server/`.

## 3. Workflow

### Idea → issue → OpenSpec change → PR

| Stage | Owner | Skill | Done when |
|---|---|---|---|
| Ground | anyone | — | the relevant `openspec/specs/` and `docs/` have been read, before the idea is discussed |
| Grill | product + engineering | `grill-me` | every open decision about the outcome is answered |
| Ticket handoff | whoever ran the grilling | `to-tickets` | GitHub issues exist with behavioural acceptance criteria, blockers and `Roadmap: X.Y`. No OpenSpec change exists yet. |
| Specify | lead agent | `openspec-propose` | one change per issue (proposal with `Roadmap: X.Y`, delta specs, design, tasks), approved by a human |
| Implement | implementer agent | `openspec-apply-change` | every task is checked off and `npm run check` is green |
| Review and close | reviewer + human | `openspec-archive-change` | every review finding is answered, the change is archived in the same PR, and a human merges |

- **Behaviour vs. engineering:** nontechnical teammates own behaviour
  (grilling, tickets, delta-spec review). Engineering owns the design and
  the tasks.
- **Behaviour changes during implementation:** update the delta spec and
  get it re-reviewed before the code relies on it.
- **Scope:** one issue per change. A new problem becomes a new issue.
- **Issue commands:** [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

### Git and CI

- **Branches and commits:** branch `feature/<step>-<slug>` off `main`. Use
  Conventional Commits. Squash-merge, one PR per issue.
- **Contract docs:** update `api-contract`, `data-contract` and
  `agents-spec` in the same PR as the code they describe.
- **One check everywhere:** `npm run check` runs type checks, tests, lint,
  format and OpenSpec checks for both Python and the frontend. CI's single
  **Check** job runs the same command. The pre-commit hook (husky +
  lint-staged) fixes and formats staged files only.
- **Deploys:** the Vercel Git integration handles them (a preview per PR,
  production from `main`, configured in `vercel.json`). There is no deploy
  workflow.

### Skills

- **Team skills** live in `.agents/skills/<name>/`, with a relative symlink
  in `.claude/skills/`, and are pinned in `skills-lock.json`.
  - Add one with
    `npx skills add <owner/repo> --agent claude-code --agent codex --skill <name>`.
  - Edit only the `.agents/` copy.
- **`openspec-*` skills** are generated per tool by `openspec update`.
  Regenerate them instead of editing them.

## 4. Agent roles (Herdr)

Specify → review runs as a supervised loop in one Herdr session:

- **Lead:** Claude Code (Opus 5, highest effort). Specifies, briefs,
  verifies every result itself, and spawns the reviewer.
- **Implementer:** Codex (`gpt-5.6-terra`, `xhigh`). Implements exactly the
  briefed tasks and reports back. Commits and opens the PR when told.
- **Reviewer:** a fresh Claude subagent. Reviews blind, against the spec
  and the standards.
- **Human:** approves the change, answers escalations and merges.

## 5. Definition of done

1. CI is green.
2. The roadmap sub-step's success-criteria scenarios pass against a running
   environment, with evidence in the PR.
3. For changes to agents, skills, instructions, MCP tools or model defaults,
   the eval report is in the PR and the evaluation-spec §6 thresholds hold.
4. For UI changes, someone other than the author ticks the ui-spec §8
   checklist.
5. The diff contains no secrets.

## 6. Session rules

1. Orient first: read this file, the issue, the checkbox state of
   `docs/roadmap.md`, and the relevant `openspec/specs/`.
2. Before writing code, state:
   - the issue;
   - the roadmap sub-step;
   - the OpenSpec change;
   - your role;
   - the layers the work touches.
3. Work within the roadmap order and your role.
4. When the spec is silent or contradictory, stop and ask. Record the answer
   in the delta spec or the relevant doc.
