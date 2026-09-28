# AGENTS.md: Marketing Automation Platform (PoC)

A Strategy agent decides what to do, and an Execution agent produces the
deliverables. Both read a Marketing Intelligence MCP over MongoDB, behind a
one-page React UI. Start with [docs/specs.md](docs/specs.md).

## Read first

| Before you… | Read |
|---|---|
| write any code | [docs/coding-conventions.md](docs/coding-conventions.md) (binding) |
| touch data, the API, agents or the UI | [data-contract](docs/data-contract.md) · [api-contract](docs/api-contract.md) · [agents-spec](docs/agents-spec.md) · [ui-spec](docs/ui-spec.md) |
| pick up work | [docs/roadmap.md](docs/roadmap.md), the Step's OpenSpec change and the relevant `openspec/specs/` |
| change agent behaviour | [docs/evaluation-spec.md](docs/evaluation-spec.md) |
| start or resume a Step or autopilot | [docs/agents/collaboration.md](docs/agents/collaboration.md) |

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
  evals/                 evaluation harness code (reads /evaluation)
  scripts/               seed, pipeline and fixture CLIs
frontend/                React + Vite service (npm workspace)
  src/                   api/ (sole backend caller), components/ds/, features/, hooks/, lib/, styles/theme.css (sole token source)
evaluation/              agent evaluation data: golden/, fixtures/, rubrics/, reports/
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

### Idea → OpenSpec change → PR

| Stage | Skill | Done when |
|---|---|---|
| Ground | — | the relevant `openspec/specs/` and `docs/` have been read, before the idea is discussed |
| Grill | `grill-me` | every open decision about the outcome is answered (only when the specs leave behaviour open) |
| Specify | `openspec-propose` (system-behaviour work) | one change for the Step lists every `Roadmap: X.Y` sub-step and every Given/When/Then scenario in its success-criteria table, with delta specs, design and tasks; outside autopilot, approved once by a human before implementation; in autopilot, reviewed by the human in the Step PR |
| Implement | `openspec-apply-change` | sub-steps are implemented in order on the Step branch; each is verified, committed and pushed before the next begins |
| Review and close | `openspec-archive-change` | the fair review meets the §4 merge bar, any OpenSpec change is archived in the same PR, and the PR is merged under that bar |

The full procedure is in [docs/agents/collaboration.md](docs/agents/collaboration.md).

- **Behaviour vs. engineering:** nontechnical teammates own behaviour
  (grilling, tickets, delta-spec review). Engineering owns the design and
  the tasks.
- **Behaviour changes during implementation:** update the delta spec and
  get it re-reviewed before the code relies on it.
- **OpenSpec scope:** system-behaviour work has at most one OpenSpec change per
  Step, and it replaces a Step issue. Discovery and doc-only work has no
  OpenSpec change; its roadmap sub-steps are the scope.
- **Issues:** only for a defect in an already-merged Step and for the human
  queue ([issue-tracker.md](docs/agents/issue-tracker.md)). A defect gets its
  own issue and a commit on the current Step's PR; it gets its own PR only
  when it breaks `main`.
- **Evaluation data** (golden datasets, fixtures, rubrics, reports) lives
  only in `evaluation/`. The harness code lives in `backend/evals/`.

### Git and CI

- **`main` is protected.** No direct commits: every change reaches `main`
  through a PR that passes **Check**.
- **Branches:** one branch per roadmap Step, named
  `feature/<step-number>-<slug>` (e.g. `feature/2-mcp-server`).
- **PRs:** one PR per Step, opened only after every sub-step is implemented
  and verified. It lists every completed sub-step (`Roadmap: 2.1, 2.2, 2.3`),
  carries evidence for every Step success-criteria scenario and is fairly
  reviewed as one whole. The Step PR itself ticks every sub-step roadmap box
  with its evidence, so the ticks land on `main` with the merge.
- **Commits:** use Conventional Commits, and squash-merge.
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

## 4. Review and merge

After the Step PR is open, a fresh reviewer subagent reviews it blind, against
the spec and the standards, with the fixed prompt in
[collaboration.md](docs/agents/collaboration.md#fair-review). Outside
autopilot, a human approves each Step's OpenSpec change before implementation
and merges. In autopilot, the human reviews the delta specs in the Step PR and
audits afterwards through the human queue.

### Merge bar

A human outside autopilot, or the agent in autopilot through
`gh pr merge --squash`, may merge only when **Check** is green, every
requirement in §5 is met, every fair-review finding is fixed or answered with
a written reason, no high-severity finding is merely answered, and every
review thread is resolved.

## 5. Definition of done

An item that does not apply to a change is marked not applicable with its
reason in the PR; that satisfies the item for the merge bar.

1. CI is green.
2. The change's scoped success-criteria scenarios pass against a running
   environment, with evidence in the PR.
3. For changes to agents, skills, instructions, MCP tools or model defaults,
   the eval report is in the PR and the evaluation-spec §6 thresholds hold.
4. For UI changes, the fair reviewer, who is not the author, verifies and
   ticks the ui-spec §8 checklist in the PR.
5. The diff contains no secrets.

## 6. Session rules

1. Orient first: read this file, the checkbox state of
   `docs/roadmap.md`, the Step's OpenSpec change and the relevant
   `openspec/specs/`.
2. Before writing code, state:
   - the roadmap Step and the sub-step in progress;
   - the OpenSpec change;
   - the layers the work touches.
3. Work within the roadmap order.
4. Outside autopilot, when the spec is silent or contradictory, stop and ask.
   In autopilot, follow [the Autopilot rules](docs/agents/collaboration.md#autopilot):
   decide reversible questions and record them in the human queue; stop only
   for the listed architectural or irreversible decisions.
