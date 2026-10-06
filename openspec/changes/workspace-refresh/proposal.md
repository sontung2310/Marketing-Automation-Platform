# Proposal: Workspace refresh and dark mode

Roadmap: 7.6, 7.7, 7.8, 7.9 · CAP-UI-01, CAP-UI-02

## Why

The owner redesigned the workspace on the Marketing Workspace design canvas
after Step 7 shipped. The canvas has a quieter type scale, panel headers with
icons and counts, card-style Strategy recommendations, a compact feed and a
dark-mode board. The running app still matches the Step 7 design, and it has no
dark mode.

## What Changes

- **Type and font:** Geist replaces Inter. The scale moves to five sizes,
  11/12/13/14/16px, and weights move from 600 to 500. This matches the canvas.
- **Dark mode:** the app follows the OS colour scheme by default. A
  `Light | Dark | System` menu in the TopBar overrides it, and the browser
  remembers the choice. Dark colours come from the canvas's dark board, with
  two contrast fixes:
  - Filled buttons keep the darker red.
  - Red type uses a light red on dark surfaces.
- **Panel headers:** every panel shows an icon, a title and a count pill. The
  Execution header shows a labelled `Working` dot while a run is in flight.
- **Social listening:**
  - Tracked keywords become list rows, with remove on hover or focus and an
    **Add keyword** control.
  - Platform tabs become a segmented control, with a trend count on each tab.
- **Strategy:**
  - **BREAKING (spec):** recommendations are no longer grouped by the run that
    produced them.
  - Each recommendation is a card. It shows a zero-padded ordinal, the
    priority, the title, up to three signal lines from its evidence
    (Trend/Competitor), and an **Open plan** button.
  - The sheet widens from 440px to 520px, and the right rail from 360px to
    425px.
- **Feed:**
  - Cards are more compact: 14px titles and small action buttons.
  - The two filters share a two-column grid.
  - The external link truncates on one line.
- **Out of scope** (no data for them yet; this is a UI-only Step):
  - per-keyword 7-day mention counts and sparklines;
  - the sheet's "The plan" dated steps;
  - the canvas's "Picked from N trends and M moves" line.

  They are recorded as a later roadmap item.
- **Kept, unlike the canvas:**
  - The composer has no agent selector (ui-spec §1.2).
  - Priority renders verbatim as `HIGH` rather than "High priority" (ui-spec §8).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `workspace-ui`:
  - layout widths (right rail 425px);
  - the token rules (five sizes, half-step spacing, light and dark themes);
  - the theme preference;
  - the Strategy presentation (cards, not run groups; 520px sheet);
  - panel headers.

## Impact

- **Frontend:**
  - `styles/theme.css`: Geist, the new scale, and dark token overrides under
    `[data-theme="dark"]`.
  - `index.html`: the Geist font and a pre-paint theme script.
  - New: a theme hook and the TopBar theme menu.
  - Changed:
    - `Panel`, `Tabs` (segmented variant) and `Button` (small size);
    - `TrackedKeywordEditor`, `TrendList`, `StrategyPanel`,
      `RecommendationSheet`, `ActivityCard`, `FeedFilters` and `ExecutionChat`;
    - Icon registry: panel icons, `plus`, `list`, `sun` and `moon`.
- **Tests:**
  - The token test gains a rule that no hex value appears outside `theme.css`.
  - Playwright adds a dark-mode axe scan and theme-toggle checks, and its width
    expectations change.
- **Backend, API, agents:** none.
- **Docs:** ui-spec §2, §3, §6, §7 and §8, and the roadmap (7.6–7.9 plus the
  deferred data item).
