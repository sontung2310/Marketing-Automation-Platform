# Design

## Context

Step 7 is brought forward ahead of Steps 3–6, so nothing the page reads
exists yet. The design problem is therefore not "how do we draw this" alone;
it is "how do we draw this so Step 6 can plug the real API in without
touching a component".

## Decisions

### 1. Column widths follow the mockup

Three sources disagreed: `docs/Marketing Workspace.html` uses
`320px minmax(560px, 1fr) 360px`, the `docs/ui-spec.md` §2 diagram is
annotated `360 / flex / 360`, and the merged `layout-workspace` utility says
`360px minmax(560px, 1fr) 320px`. The mockup is the owner's redesign and the
most recent artifact, and its asymmetry is deliberate: the right rail stacks
Strategy recommendations over the feed and needs the extra 40px, while the
left rail holds a keyword editor and two compact tables. The mockup wins;
the spec diagram and the token file are corrected to match in this change.

### 2. `src/api/` always speaks HTTP; MSW stands in for the services

The alternative — a fixture transport selected inside `src/api/` by a Vite
flag — puts a permanent branch in the layer the conventions want thinnest,
and leaves dead code once Step 6 lands. Instead every module in `src/api/`
calls the real `/api` path unconditionally, and one typed handler set in
`src/test/fixtures/` serves those paths through MSW in three places: the
browser service worker in dev mode, the node server in Vitest, and the same
node server behind Playwright. Turning MSW off is the whole migration.

The handlers are typed against the same `src/api/types.ts` the components
consume, so a fixture that drifts from the contract fails the type check
rather than the eye.

### 3. Server state goes through TanStack Query; nothing else is global

`docs/coding-conventions.md` §6 already requires it, and it is what makes
§5's state table one pattern instead of five: `isPending` drives the
skeleton, `isError` drives the verbatim message plus **Retry**, an empty
`items` array drives the empty state, and `useInfiniteQuery` drives the
feed's cursor pagination. Live inserts and run events are not queries — they
are `EventSource` subscriptions in hooks that write into the query cache, so
the feed has exactly one source of truth.

The only cross-region state is the Execution composer draft and the session
ID, which live in one `WorkspaceProvider` context because **Do this** in the
right region must reach the composer in the centre.

### 4. Type-keyed rendering goes through registries, never branches

Nine activity types, eight channels, ten deliverable types, five
recommendation kinds, three priorities and four quality statuses all render
differently. Each is a `Record<Enum, …>` lookup in one place with an
exhaustiveness check from the enum union, so adding an enum value is a
compile error rather than a missing case. The activity → action mapping is
the exception that proves it: the server computes `actions[]`, so the UI
holds no mapping at all.

### 5. The design system is rebuilt from the mockup's computed values

The mockup ships inline styles. Every distinct value in it was checked
against `theme.css`; all of them already have tokens except the column
widths above. The primitives in `components/ds/` are therefore a faithful
port with the inline styles replaced by token utilities, which is what makes
the §8 anti-slop checklist mechanically checkable by ESLint rather than by
review alone.

### 6. Playwright now, Lighthouse deferred

Four of Step 7's six criteria name Playwright, and Step 8.1 needs it anyway.
Lighthouse CI's accessibility score needs a real served environment and adds
a heavy, flaky CI dependency for one number. `@axe-core/playwright` runs in
the specs that already exist, gates on zero violations, and is a stricter
check than the 90 threshold for the rules it covers. The Lighthouse number
is marked not applicable until Step 8 stands up the real environment.

## Risks / Trade-offs

- **Fixtures can drift from the eventual API.** Mitigated by typing the
  handlers against the shared contract types, and by Step 6.6 regenerating
  those types from the OpenAPI export — which will surface any drift as a
  type error in the handlers.
- **MSW in dev mode can mask a broken backend.** It is enabled only by an
  explicit `VITE_USE_FIXTURES` dev-mode flag and is never bundled into a
  production build.
- **SSE under MSW.** MSW streams the run and activity event sources as
  chunked responses; the app's `EventSource` usage is unchanged, so the
  fixture path exercises the same parsing code the real API will feed.

## Migration Plan

None. This change adds a frontend that had no users.
