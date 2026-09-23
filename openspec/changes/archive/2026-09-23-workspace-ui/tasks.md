# Tasks

## Roadmap scenario mapping

| Roadmap scenario | Task(s) that prove it |
|---|---|
| 7-A | 6.1 — Playwright load spec at 1440×900 with the axe gate |
| 7-B | 3.5 — one Vitest component test per `ActivityType` |
| 7-C | 6.2 — Playwright streaming-transcript spec |
| 7-D | 6.3 — Playwright Do-this and evidence-chip spec |
| 7-E | 6.4 — Playwright region-failure and viewport spec |
| 7-F | 7.3 — the PR's ui-spec §8 checklist, signed by the fair reviewer |

## 7.1 — Design-system primitives and tokens

- [x] 1.1 Correct `layout-workspace` in `frontend/src/styles/theme.css` to
  `320px minmax(560px, 1fr) 360px` at the desktop breakpoint, add the named
  utilities the workspace needs that cannot be expressed as token classes
  (transcript height, sheet width, evidence flash, shimmer), and correct the
  `docs/ui-spec.md` §2 diagram to the same widths.
- [x] 1.2 Add the dependencies: `@tanstack/react-query` as a runtime
  dependency, and `msw`, `@playwright/test` and `@axe-core/playwright` as dev
  dependencies.
- [x] 1.3 Build the token-only primitives in `frontend/src/components/ds/`:
  `Button` (primary, secondary, quiet, icon), `Card`, `Panel`, `Badge`,
  `Tabs`, `SegmentedSwitcher`, `Table`, `TextInput`, `Menu`, `Sheet`,
  `Skeleton`, `EmptyState`, `ErrorState` and `LiveRegion`. Every variant is a
  `Record<Variant, string>` lookup composed with `cn()`.
- [x] 1.4 Add a Vitest suite asserting the primitives carry no inline style
  and no arbitrary Tailwind value, so §8's token-only rule is mechanical.

## 7.2 — Layout shell

- [x] 2.1 Add `src/api/types.ts` typed by hand against
  `docs/api-contract.md` and `docs/data-contract.md` §2, including every
  enum as a union with its exhaustiveness helper.
- [x] 2.2 Extend `src/api/client.ts` with `postJson`, `putJson` and the
  typed error envelope, and add one module per resource (`company`,
  `activities`, `trends`, `influencers`, `recommendations`, `runs`,
  `sessions`, `actions`).
- [x] 2.3 Add the typed MSW handler set and fixture data in
  `src/test/fixtures/`, covering the seeded company, ≥ 1 activity per
  `ActivityType`, trends, influencers, recommendations, a session and two
  streamed runs. Wire it into Vitest setup, a `VITE_USE_FIXTURES` dev-mode
  browser worker, and Playwright.
- [x] 2.4 Build `TopBar` with the tenant selector, context label, last-sync
  label and `SimulateMenu` listing the nine `ActivityType` values plus
  `Random`, with a labelled in-flight state.
- [x] 2.5 Build the `WorkspaceShell` grid, the `WorkspaceProvider` holding
  the composer draft and session ID, the `QueryClientProvider`, and the
  900px `Feed | Workspace | Insights` switcher.

## 7.3 — Social listening and the competitor feed

- [x] 3.1 Build `TrackedKeywordEditor` with trim, empty rejection, 1–20
  bounds, case-insensitive uniqueness, the canonical list from the response,
  and text validation messages.
- [x] 3.2 Build the channel-tabbed `TrendRow` list with topic, channel,
  mention count, signed momentum with its arrow, and **Get topic ideas**.
- [x] 3.3 Build the two-column `InfluencerTable` with monogram, linked
  handle, channel, compact followers and **Draft outreach**, and no avatar
  images.
- [x] 3.4 Build `ActivityFeed` and `ActivityCard`: type and competitor
  filters, `useInfiniteQuery` cursor pagination, the unseen count, the
  mark-seen call after 2 s at the top, and the `actions[]` buttons rendered
  from the server.
- [x] 3.5 Add the per-`ActivityType` Vitest component tests proving 7-B,
  plus tests for the price delta, the author line and the mock and simulated
  badges.
- [x] 3.6 Add `useActivityStream`, inserting `activity.created` items at the
  top of the query cache with the polite live-region announcement and the
  bounded-backoff reconnect bar.

## 7.4 — Execution chat

- [x] 4.1 Build `ExecutionChat`: the fixed-height transcript, the docked
  composer with its auto-growing textarea, the `Auto | Strategy | Execution`
  menu, the try chips and the Enter/Shift+Enter behaviour.
- [x] 4.2 Build `ExecutionTurn`: the agent label and trigger, the collapsed
  thinking and tool line expanding to the reasoning and one row per tool,
  the streaming shimmer with its elapsed time, and the answer.
- [x] 4.3 Build `DeliverableCard` with type, channel, title, word count, the
  sanitized markdown body, variants, **Copy** and the four quality statuses
  rendered as text, not color alone.
- [x] 4.4 Build `ProposedActionRow` with the editable `scheduled_for`,
  **Discard**, **Approve**, and the `EXECUTED` receipt and `mock` label.
- [x] 4.5 Build `ClarificationBlock` and the refusal block, including the
  Strategy-shaped question that points at the feed instead of entering the
  transcript.
- [x] 4.6 Add `useRunStream` with `Last-Event-ID` replay, and restore the
  session from `localStorage` through `GET /sessions/{id}` on load,
  reattaching any `RUNNING` run.

## 7.5 — Strategy panel and the evidence loop

- [x] 5.1 Build `StrategyPanel` with recommendation rows grouped by their
  run, showing ordinal, priority, decision, status and `next_action`.
- [x] 5.2 Build `RecommendationSheet` at 440px with what to do, why,
  evidence chips and **Do this**, writing the brief into the composer
  without sending.
- [x] 5.3 Build `EvidenceChip` with its short title, the raw ID in the
  tooltip, and the scroll-to and flash-highlight behaviour through a
  registry of evidence kinds.

## 7.6 — Verification

- [x] 6.1 Add the Playwright config, the MSW-backed fixture server and the
  1440×900 load spec with the axe gate, proving 7-A.
- [x] 6.2 Add the streaming-transcript spec proving 7-C, including the
  10-second no-silent-gap assertion.
- [x] 6.3 Add the Do-this and evidence-chip spec proving 7-D, asserting no
  run is created.
- [x] 6.4 Add the region-failure and viewport spec proving 7-E: a `503`
  envelope rendered verbatim with **Retry**, the other regions still usable,
  the 900px switcher, and no horizontal body scroll.
- [x] 6.5 Wire `npm run test:e2e` into the root task runner and add the
  browser install step to the CI Check job.

## 7.7 — Close out

- [x] 7.1 Update `docs/ui-spec.md` §2 and any component note the build
  changed, in this PR.
- [x] 7.2 Tick the Step 7 sub-step boxes in `docs/roadmap.md` with their
  evidence.
- [x] 7.3 Run `npm run check`, open the Step PR with the evidence for 7-A
  through 7-E and the ui-spec §8 checklist for the fair reviewer, and
  archive this change in the same PR.
