# Design: Workspace refresh and dark mode

## Context

The source of truth is the **Marketing Workspace** design canvas, with boards
`Main.dc.html` (light) and `Dark.dc.html`. The dark board has the same markup
as the light one: only colour values change, 230 colour slots one-to-one. So
dark mode is a remap of colour tokens, not separate components.

The app is styled only through Tailwind v4 utilities generated from `@theme`
in `frontend/src/styles/theme.css`, and those utilities read `var(--color-*)`
at runtime. `tokens.test.ts` enforces no inline style and no arbitrary values
in `components/ds/`.

## Goals / Non-Goals

**Goals:** match the canvas at 1440×900 in both themes, keep a single token
source, and keep every Step 7 behaviour (states, evidence loop, breakpoints,
axe-clean).

**Non-Goals:**
- No new API fields: no keyword stats and no recommendation plan steps.
- No per-component dark variants.
- No composer agent selector.

## Decisions

### D1. Dark mode is a token override on `:root[data-theme="dark"]`

`theme.css` adds one block that redefines the colour tokens, plus
`color-scheme: dark`. Components keep using the same semantic utilities, such
as `bg-surface-card` and `text-text-muted`, so no component needs a `dark:`
variant.

*Alternative:* Tailwind `dark:` variants on each component. That doubles every
colour class across about 40 files and invites drift. Rejected.

The values come from the canvas mapping, with fixes where the canvas fails AA:

| Token | Light | Dark |
|---|---|---|
| `bg` (cards) | `#fff` | `#1b1c20` |
| `bg-subtle` | `#f7f7f8` | `#24252a` |
| `surface-page` | = `bg-subtle` | `#111214` (own value in dark) |
| `text` / `text-muted` | `#1a1a1a` / `#6b7280` | `#ececee` / `#9aa0a8` |
| `border` / `border-strong` | `#e5e7eb` / `#d1d5db` | `#2c2d33` / `#3a3c42` |
| `primary-light` / `secondary-light` | `#fde8e5` / `#e3f7ef` | `#3b1d1a` / `#12302a` |
| `surface-ink` (TopBar) | `#16171a` | `#c42e22` (the canvas's red band) |
| `text-inverse` / `-muted` | `#f2f3f5` / `#9aa0a8` | `#fff` / a light tint ≥ 4.5:1 on `#c42e22` (the canvas's 82% white is 4.08:1, a **fix**) |
| `text-favorable` / `-attention` / `-unfavorable` | unchanged | `#4ade80` / `#f5b04c` / `#f87171` (canvas `#dc2626` is 4.1:1, a **fix**) |
| `text-accent` (new: red type, e.g. ordinals) | `#c42e22` | `#ff8a7f` (canvas `#e4362a` as type is 3.9:1, a **fix**) |
| shadows | 6–14% ink | 30–50% black |

Filled buttons stay `primary-hover` `#c42e22` with white text (5.58:1) in both
themes. The canvas's dark board uses `#e4362a` (4.32:1), which is a **fix**.

### D2. The theme is resolved before first paint by a tiny inline script

`index.html` gets a script of about 10 lines that runs before the bundle. It
reads `localStorage.theme`, which is `light` or `dark`; any other value means
no stored choice. Without a stored choice it falls back to
`matchMedia('(prefers-color-scheme: dark)')`, then sets
`document.documentElement.dataset.theme`. Storage access is wrapped in
try/catch, so a blocked store falls back to the system preference.

A `useTheme` hook in `hooks/` owns the preference afterwards:
- it reads and writes the same key;
- it re-applies the attribute;
- in `System` mode, it subscribes to the media query so OS changes apply live.

The TopBar gets a `Menu` with three `MenuItem checked` options. It reuses the
existing `Menu`, so no new primitive is needed.

*Alternative:* resolve the theme in React only. That causes a white flash on
dark systems. Rejected.

*Alternative:* a CSS `@media (prefers-color-scheme)` block as well as the
attribute. That duplicates the token block. Rejected: the script always sets
the attribute.

### D3. Type: Geist, five sizes, weight 500

`--font-sans` becomes `"Geist", …fallbacks`, loaded from Google Fonts in
`index.html` in place of Inter. The size tokens are remapped:

- `text-micro`: 11px (new)
- `text-small`: 12px
- `text-body`: 13px
- `text-h3`: 14px
- `text-h2`: 16px

`text-h1` (32px) has zero uses and is dropped, which keeps the count at five.
Remapping the sizes in place moves most of the UI with no class changes. Each
`font-semibold` (33 uses) becomes `font-medium`, the canvas's 500. Label
tracking goes from 0.06em to 0.05em.

### D4. Panel header carries an icon and a pill

`Panel` gains a required `icon: IconName` prop and renders the canvas header:
- a 24px framed icon tile;
- a 13px medium title in sentence case, no longer uppercase;
- `meta` in a pill.

The Icon registry gains the canvas's five panel glyphs: `radio`, `users`,
`pen`, `target` and `pulse`. It also gains `plus`, `list`, `sun` and `moon`.
`ExecutionChat` passes the request count as meta, with a labelled `Working`
dot before it while a run is in flight.

### D5. Strategy becomes cards; signals come from evidence

The grouping by `run_id` is removed. Each card is laid out from data the API
already returns:
- `ordinal` zero-padded;
- `priority` in a `Badge`, verbatim;
- `title`;
- signal lines mapped from `evidence[]`, at most three, through a registry
  keyed by `evidence.kind`. `trend` maps to `Trend` (favorable tile) and
  `activity` to `Competitor`; `influencer` and `company` are labelled too, so
  every kind is covered. The `note` is the line text.

**Open plan** is a secondary button that opens the sheet. The sheet width
utility goes from 440px to 520px.

### D6. Layout and sizes live in named utilities

The right column goes from `360px` to `425px` in `layout-workspace`, at both
desktop and tablet. The centre becomes `minmax(0, 1fr)`, as on the canvas:
with 560px, the desktop arrangement overflowed at 1281–1384px. `sheet-width` becomes 520px, capped at the viewport less its 24px gutters so it
never runs off a phone screen. Below the tablet breakpoint the TopBar keeps only
its controls: the context label and last-sync text hide, and the theme and
Simulate triggers shorten, each keeping its accessible name. Keyword rows use a new
`layout-keyword-row` utility, `20px 1fr 20px`: the canvas's sparkline and
count columns are dropped (non-goal). Spacing stays on the 8px unit, with
half steps (4px and 12px) allowed. The canvas uses 12px card padding.

### D7. Enforce "no literal colour" mechanically

`tokens.test.ts` widens its scope from `components/ds/` to all `src/**/*.tsx`.
It adds a rule that no `#rgb`/`#rrggbb` literal appears outside `theme.css`. A
stray hex would break dark mode silently, so this rule is the guard.

## Risks / Trade-offs

- **[Risk]** A hard-coded `bg-white` or `text-white` stays white in dark mode.
  → `--color-white` is used only for type on filled red. The implementation
  audits each use of `white` and `surface-ink`.
- **[Risk]** Geist from Google Fonts adds a network dependency.
  → The same applies to Inter today, and the font stack falls back to system
  fonts.
- **[Trade-off]** The canvas's sparklines, mention counts and plan steps are
  not shown, so the app will look sparser than the canvas in those spots.
  → These are recorded as a deferred roadmap item, and the canvas stays the
  target.
- **[Trade-off]** Priority renders as `HIGH`, not "High priority".
  → This keeps the owner's verbatim-enum rule. It is flagged for the owner to
  overrule.

## Migration Plan

Frontend only. Deploy through the Vercel preview, and roll back by reverting
the PR. A stored `theme` key does no harm if the feature is reverted.
