# Proposal

Roadmap: 7.1, 7.2, 7.3, 7.4, 7.5

## Why

The specification half of Step 7 (#26) recorded the owner's workspace
redesign in `docs/ui-spec.md`, but nothing renders it. `frontend/` still
holds the three-panel placeholder shell from Step 0, whose column order,
component set and states all predate the redesign.

Step 7 is brought forward ahead of Steps 3–6, so the Platform API, the
classifier router and the agents do not exist yet. The workspace is
therefore built against typed fixtures that stand in for those services and
are replaceable by them without changing the visual contracts.

## What Changes

- Rebuild `frontend/src/components/ds/` as the token-only Tailwind design
  system the workspace needs: button tones, card, panel, badge, tabs,
  segmented switcher, table, input, menu, sheet, skeleton, empty state and
  error state.
- Replace the placeholder `App` with the workspace shell: an inverted,
  logo-free TopBar (tenant selector, context label, last sync, Simulate
  menu) over a three-region grid at `320px / minmax(560px, 1fr) / 360px`,
  with the documented 1280px and 900px responsive behaviour.
- Build social listening (tracked-keyword editor, channel-tabbed trends,
  two-column influencer table) and the competitor activity feed (type and
  competitor filters, cursor pagination, live SSE inserts, NEW/seen state).
- Build the Execution chat: a fixed-height transcript with a docked
  composer, marketer-only bubbles, the agent selector, a collapsed
  thinking/tool trace that expands per tool call, the answer, the
  deliverable block with its four quality checks, proposed-action approval,
  and clarification and refusal blocks. Restore the session from
  `localStorage` on load.
- Build the Strategy panel and the evidence loop: compact recommendation
  rows grouped by run, a 440px detail sheet, **Do this** prefilling the
  composer without sending, and evidence chips that scroll to and
  flash-highlight their target.
- Add `src/api/` modules for every endpoint the page needs, typed by hand
  against `docs/api-contract.md` until Step 6.6 generates them from the
  OpenAPI export, and route every region's server state through TanStack
  Query so loading, empty, error and **Retry** states come from one pattern.
- Add one typed MSW fixture set that serves those endpoints in dev mode,
  Vitest and Playwright, and add Playwright with an axe accessibility gate.
- Correct the column widths in `docs/ui-spec.md` §2 and the
  `layout-workspace` utility to the mockup's `320 / flex / 360`, resolving
  the three-way disagreement between the mockup, the spec diagram and the
  merged token file.

## Capabilities

### New Capabilities

- `workspace-ui`: CAP-UI-01, CAP-UI-02 and CAP-UI-03 — the single-page
  marketing workspace, its three regions, its agent transcript and the
  evidence loop between Strategy and Execution.

### Modified Capabilities

- None.

## Impact

- Affected code: `frontend/src/` (components, features, hooks, api, test
  fixtures and Playwright specs), `frontend/package.json`,
  `frontend/src/styles/theme.css`, the root `package.json` test scripts and
  the CI workflow's browser install step.
- New runtime dependency: `@tanstack/react-query`. New dev dependencies:
  `msw`, `@playwright/test`, `@axe-core/playwright`.
- Doc updates in the same PR: `docs/ui-spec.md` §2 column widths and
  `docs/roadmap.md` Step 7 boxes and evidence.
- No backend, API, agent, MCP or data-contract change. The API shapes the
  fixtures serve are exactly those in `docs/api-contract.md`, so Step 6 can
  replace the fixture transport without touching a component.
