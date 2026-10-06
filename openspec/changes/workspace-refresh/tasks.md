# Tasks

## 1. Tokens, type and dark mode (Roadmap 7.6)

- [x] 1.1 Remap the type tokens in `theme.css` per design D3:
  - Geist font;
  - `text-micro`, 11/12/13/14/16, and drop `text-h1`;
  - tracking 0.05em.

  Swap Inter for Geist in `index.html` and replace `font-semibold` with
  `font-medium` throughout. Verify with `npm run check` and visually at
  1440×900.
- [x] 1.2 Add the dark token block on `:root[data-theme="dark"]` with the D1
  values, including the `text-accent`, `text-inverse-muted` and status-text
  fixes. Verify that each pair in the D1 table is ≥ 4.5:1 with a contrast
  script whose output goes in the PR.
- [x] 1.3 Add the pre-paint theme script to `index.html`, the `useTheme` hook
  and the TopBar `Light | Dark | System` menu (D2), with the `sun` and `moon`
  icons. Verify with Vitest for the hook: stored override, `System` clears it,
  and a media change applies live.
- [x] 1.4 Widen `tokens.test.ts` to all `src/**/*.tsx` and add the
  no-hex-literal rule (D7). Fix any offenders. Verify that the test fails on a
  planted `#fff` and then passes.
- [x] 1.5 Add the Playwright dark scenarios: the system-dark load with an axe
  scan, and pick `Dark` → reload → `System`. Verify that
  `npm run test:e2e` passes.

## 2. Panel headers and social listening (Roadmap 7.7)

- [x] 2.1 Add a required `icon` to `Panel` and render the framed icon tile,
  the sentence-case title and the meta pill (D4). Add the five panel glyphs
  plus `plus` and `list` to `Icon`. Update every `Panel` call site. Verify
  that the Playwright 7-A test asserts each header's title and pill.
- [x] 2.2 Rebuild `TrackedKeywordEditor` as list rows (`layout-keyword-row`).
  The remove control shows on hover or focus. **Add keyword** reveals the
  existing labelled input, and validation is kept. The canvas's undo line is not added, because the spec doesn't ask for one. Verify
  that the duplicate-keyword scenario still passes, plus a new keyboard-remove
  test.
- [x] 2.3 Add a `segmented` variant to `Tabs` and use it for the trend
  platform filter, with per-tab counts from the trends already loaded for
  `ALL`. Restyle trend and influencer rows to the new scale. Verify with a
  Vitest test for the counts and with `npm run check`.

## 3. Execution, Strategy and the right rail (Roadmap 7.8)

- [x] 3.1 Change the right column to 425px in `layout-workspace` and the sheet
  to 520px (D6). Verify that the Playwright width assertions are updated and
  pass.
- [x] 3.2 Make the `ExecutionChat` header show the labelled `Working` dot
  while a run is in flight, else the request count. Move the prompt chips centred above the composer and always show them, as on
  the canvas. Verify that the 7-C Playwright test still passes.
- [x] 3.3 Rebuild `StrategyPanel` as cards per D5:
  - no run grouping;
  - an evidence-kind registry for the signal lines;
  - **Open plan**;
  - the header counts the cards shown.

  Restyle `RecommendationSheet` with `Based on` and kind-labelled chips.
  Verify the new "card summarises its signals" Vitest, and that the 7-D
  Playwright test passes at 520px.

## 4. Feed, docs and evidence (Roadmap 7.9)

- [ ] 4.1 Compact `ActivityCard` to the canvas: 14px title, a small primary
  button and a single-line truncated link. Put `FeedFilters` in a two-column
  grid. Verify that `ActivityCard.test.tsx` (7-B) passes.
- [ ] 4.2 Update ui-spec:
  - §2: layout widths;
  - §3: Panel, keyword editor, Strategy cards, 520px sheet, theme menu;
  - §6: dark-mode contrast;
  - §7: theme deviations;
  - §8: five sizes, half-step spacing, no literal colours, both themes
    checked.

  Update the roadmap: tick 7.6–7.9 with evidence, and add the deferred item
  for keyword stats and plan steps. Verify with `npm run openspec:check`.
- [ ] 4.3 Capture evidence: 1440×900 screenshots in light and dark next to
  the canvas boards, the full Playwright and axe run in both themes, and
  `npm run check` green. Attach them to the PR.
- [ ] 4.4 Fix the canvas's two dark contrast issues (filled button, red type)
  so the design and the app agree. Verify that the canvas dark board uses
  `#c42e22` fills and `#ff8a7f` red type.

No agents, skills, instructions or MCP tools change, so no eval suite runs.
