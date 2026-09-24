# Proposal

## Why

Roadmap: 3.1, 3.2. The Strategy and Execution agents need a trustworthy,
repeatable catalogue of marketing methods, but no skill files or safe loading
boundary exist yet. Vendoring a pinned subset now gives both agents the same
reviewable source material while keeping allowlists, reference access and
per-run budgets enforceable before agent implementation begins.

## What Changes

- Add the 12-skill subset named in `docs/agents-spec.md §4.1` under
  `backend/app/skills/library/`, preserving each skill's references and evals.
- Add a lockfile containing the upstream commit and a content hash per skill,
  plus an update/check CLI that detects hand edits or upstream drift.
- Add a typed loader that parses frontmatter, returns a skill body or one
  in-directory reference, and appends the product-context note.
- Add `list_skills` and `load_skill` tools for both agents, enforcing their
  configured allowlists and a maximum of three loads per run.
- Update the relevant agent/spec/roadmap documentation and add deterministic
  unit and contract tests for loading, allowlists, limits and hash checking.

## Capabilities

### New Capabilities

- `marketing-skills-library`: pinned, parsed, allowlisted marketing skills and
  bounded `list_skills`/`load_skill` tools for the Strategy and Execution
  agents (CAP-SKL-01).

### Modified Capabilities

None.

## Impact

The change adds files under `backend/app/skills/`, the skills update/check CLI,
agent tool wiring/configuration, tests, and the contract/roadmap documentation.
It adds no database access, API endpoint, MCP tool, connector, or external
write path. The upstream source is fetched only by the maintenance CLI; the
runtime loader reads the committed local catalogue. The Strategy and Execution
evaluation suites do not exist until Steps 4–5, so the implementation PR will
record evaluation-spec §6 as not applicable and provide the loader/tool test
evidence instead.
