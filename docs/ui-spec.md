# UI Specification — Single-Page Marketing Workspace

> Parent: [specs.md](specs.md) · API: [api-contract.md](api-contract.md)
> Design system: **CompetitorScope Design System**
> (`../Competitors-Monitoring/design/CompetitorScope Design System/`). Its
> `readme.md` is binding for color, type, spacing, shape, motion, iconography
> and content voice. This document covers the page-specific workspace and its
> deliberate deviations from that system.
> Visual target: the owner's **Marketing Workspace** design canvas, with a
> light and a dark board at 1440×900.

## 1. Principles

1. **One page, three jobs.** Social listening is on the left, Execution chat
   is in the centre, and Strategy plus competitor evidence is on the right.
   There is no route change for these jobs.
2. **Execution owns the conversation.** The centre transcript belongs to the
   Execution agent, and there is nothing in it to route elsewhere: the
   composer has no agent selector. Strategy recommendations stay in their own
   panel and are handed to Execution through an explicit user action, and
   Strategy runs are started from **Generate strategy** in the Strategy panel, a feed item or a trend.
3. **Evidence is clickable.** Every evidence chip scrolls to and highlights
   its feed item or insight row. A chip may cite an item further down the feed
   than the pages loaded so far, so following one closes the sheet and the feed
   pages forward until the target exists.
4. **Every button says where it goes.** Buttons name the outcome, such as
   `Draft a CEO post` or `Plan a response`, and the run header names the agent
   and route reason.
5. **Design-system discipline.** Cards are flat, spacing follows the 8px
   grid, enums render verbatim, and decorative emoji are limited to 🧪
   `SIMULATED` and 🎭 `Simulate`.

## 2. Layout

The design target is 1440×900.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ TopBar: [Marketing Eye ▾]  Marketing workspace  Last sync 3 min ago [System ▾] [🎭 Simulate ▾] │
├──────────────────────────────┬──────────────────────────────────┬────────────────────────┤
│ SOCIAL LISTENING              │ EXECUTION                        │ STRATEGY               │
│ Tracking keywords [edit]      │ fixed-height transcript           │ Recommendations         │
│ [ai search] [content …]       │ marketer: Write the LinkedIn…    │ 1 · HIGH               │
│ Trends                        │ EXECUTION · CREATE_SIMILAR        │ Decision at body weight│
│ AI search visibility ▲142%    │ ✓ Loading company context        │ Next action             │
│ [Get topic ideas]             │ ┌ Deliverable · CEO_POST ┐        │ [Do this]               │
│ Influencers                   │ │ body… [Copy]          │        │                        │
│ Influencer          Followers │ │ PASS PASS FIXED PASS  │        │ Competitor activity    │
│ @handle · LINKEDIN     48.2K │ │ [Discard] [Approve]   │        │ [All types ▾][All comps]│
│                              │ └───────────────────────┘        │ ┌ Activity card ──────┐ │
│                              │ Ask for a deliverable…            │ │ NEW_BLOG             │ │
│                              │ Ask for a deliverable… [Send]      │ │ Brightlane · Web     │ │
│                              │                                    │ │ [Create similar]     │ │
└──────────────────────────────┴──────────────────────────────────┴────────────────────────┘
       320px fixed                         flex                         425px fixed
```

- The page ground is `--surface-page`. The three working regions are card
  panels with a 1px border. Each panel header shows a framed icon, the title
  in sentence case and a count or status pill. Gutters are 16px and page
  padding is 24px. At the 1440×900 design target the grid is
  `320px / minmax(0, 1fr) / 425px`: the right rail stacks Strategy cards over
  the feed and needs the extra width, the left rail holds a keyword list and
  two compact tables, and the centre absorbs the rest, so the body never
  scrolls sideways down to the 1281px desktop breakpoint.
- The left region contains tracking keywords, trends and influencers. The
  right region puts Strategy recommendations above the competitor activity
  feed. The centre region is the only chat transcript.
- Each region scrolls independently. The TopBar is sticky. The Execution
  composer is docked to the bottom of the centre transcript.
- The TopBar has no logo. It contains the tenant selector, context label, last
  sync time, the theme menu and the Simulate menu.
- **Themes:** light and dark. With no saved choice the page follows the
  operating system's colour scheme, live. The TopBar's `Light | Dark | System`
  menu overrides it; the choice persists in this browser, and `System` clears
  it. The theme is resolved before first paint. The dark theme remaps the same
  tokens (`frontend/src/styles/theme.css`), so no component has a dark variant.
- **Responsive:**
  - At 1280px and below, the left social-listening region becomes a tab in the
    workspace shell while Strategy and the feed remain available.
  - At 900px and below, the page is one column with a bottom segmented switcher
    `Feed | Workspace | Insights`.
  - Below 901px, the TopBar keeps only its controls: the context label and
    last-sync text hide, and the theme and Simulate triggers shorten.
  - At every width, the body never scrolls horizontally.

## 3. Components

Components are rebuilt as Tailwind components in
`frontend/src/components/ds/`, using only token utilities from
`frontend/src/styles/theme.css` (see
[coding-conventions.md §6](coding-conventions.md#6-frontend-react-vite-and-tailwind)).

| Component              | Built from                  | Notes                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TopBar`               | DS controls                 | Tenant selector, `Marketing workspace` context label, last-sync meta text, the `Light \| Dark \| System` theme menu and the Simulate menu. Ink band in light, brand red in dark. No logo. |
| `SimulateMenu`         | DS `Button` + overlay       | Lists all 9 `ActivityType` values plus `Random`; shows a labelled `Simulating…` state while the request is in flight.                                                                                                                                                                                                                                           |
| `SocialListeningPanel` | DS `Panel`, `Input`, `Tabs` | Tracked-keyword list in the header, then Trends and Influencers panels. The header pill counts keywords and trends. Keywords scope social listening only; they do not filter the competitor feed. |
| `TrackedKeywordEditor` | DS list rows + quiet controls | One row per term with a tag glyph; the labelled remove control shows on row hover or keyboard focus. **Add keyword** reveals the labelled input and moves focus into it. Shows five seeded terms, trims on save, rejects empty values, and enforces 1–20 case-insensitively unique terms. |
| `TrendRow`             | DS row primitives           | Topic, channel, momentum with arrow and sign, mention count and a **Get topic ideas** quiet button. Filtered by a segmented platform control whose options show their trend counts. |
| `InfluencerTable`      | DS table                    | Exactly two visible columns: Influencer and Followers. Each row shows the round avatar (`avatar_url`, lazy, empty `alt`; the monogram when it is null or fails to load), linked handle, channel, compact followers, engagement and up to three topic labels, plus **Draft outreach**. Rows keep the API order (DCT score, then followers).                                                                                                                                                |
| `ExecutionChat`        | DS `Panel`, `Input`         | Fixed-height, independently scrolling transcript. The header shows a labelled `Working` status while a run streams, and the request count. Three prompt chips sit centred above the docked composer, which offers an auto-growing textarea (max 6 lines) and **Send**. There is no agent selector: the centre belongs to the Execution agent alone, Strategy is reached from a feed item, and a strategy-shaped message comes back as one clarification line pointing at the feed. |
| `ExecutionTurn`        | Structured blocks           | Shows the `EXECUTION` label and trigger, one collapsed line for thinking/tool calls that expands to reasoning and one row per tool, then the answer and deliverable block. Only marketer messages may use a quiet bubble.                                                                                                                                       |
| `DeliverableCard`      | DS `Card`                   | Type, channel, title, sanitized markdown body, word/character count, **Copy**, variants, four quality statuses and proposed-action controls.                                                                                                                                                                                                                    |
| `ProposedActionRow`    | DS buttons                  | Editable schedule (`scheduled_for` for social posts, `date` for calendar entries), **Discard** and **Approve**. Approval ends with `EXECUTED`, receipt ID and `mock`, or a terminal `FAILED` row showing `error`.                                                                                                                                               |
| `ClarificationBlock`   | DS secondary buttons        | One clarification line with 2–3 quick replies. A Strategy-shaped question points at the feed instead of entering the Execution transcript.                                                                                                                                                                                                                      |
| `StrategyPanel`        | DS cards + sheet            | The header holds the picks pill (or the working status) and **Generate strategy**. Above the cards, **Latest analysis** shows the latest successful Strategy run's answer, implications and gaps for the page session, so **Why it matters** is visible without cards. One card per `OPEN` recommendation of the company-wide set, not grouped by run: zero-padded ordinal, priority verbatim, title, the `insight` (two lines), "For <audience>", up to three signal lines from its evidence (`Trend`, `Competitor`, `Influencer`, `Company` with the note) and an **Open plan** button. The sheet shows the insight and the audience above the rationale. While any Strategy run is in flight, **Generate strategy** and every item action whose agent is Strategy are disabled. |
| `RecommendationSheet`  | DS pop-out sheet            | 520px wide. Shows what to make, the channel, why, `Based on` evidence chips and **Do this**. Clicking **Do this** writes the request into the Execution composer without sending it. |
| `EvidenceChip`         | DS pill                     | Displays the evidence kind and a short title, and keeps the raw evidence ID in a tooltip. Click scrolls to and flash-highlights the target item. |
| `ActivityFeed`         | DS `Card`, `EmptyState`     | Header, unseen count, type and competitor filters, newest-first cursor pagination, live inserts and seen state. Lives below Strategy on the right.                                                                                                                                                                                                              |
| `ActivityCard`         | DS `Card`, badges           | Type, relative time, competitor/channel, two-line 14px title, conditional author or price delta, safe external URL truncated to one line, a small primary action from `actions[]` with a quiet secondary beside it, and `MOCK`/`🧪 SIMULATED` badges. |
| `ActivityTypeBadge`    | DS `ChangeTypeBadge`        | Covers all 9 `ActivityType` values using existing tones; no new colors.                                                                                                                                                                                                                                                                                         |

**Until the Platform API exists** (Step 7 is brought forward ahead of Step 6),
`frontend/src/api/` still calls the real `/api` endpoints and typed MSW
handlers in `frontend/src/test/fixtures/` serve them in dev mode, Vitest and
Playwright. Removing that layer is the whole migration; no component changes.

## 4. Interaction flows

| Trigger                       | Request                                                     | Immediate UI response                                                                                                                                                                                           |
| ----------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Feed primary/secondary button | `POST /runs {trigger: {kind: FEED_ACTION, ref_id, action}}` | A new run appears in the Execution transcript; the source card briefly shows `Sent to workspace`.                                                                                                               |
| Chat send                     | `POST /runs {message}`                                      | The marketer's message appears above a new Execution turn. The UI sends no `agent_hint`: everything typed here is for Execution. A `200` clarification or out-of-scope response renders without creating a run. |
| **Generate strategy**         | `POST /runs {trigger: {kind: COMPANY, ref_id: <company>, action: GENERATE_STRATEGY}}` | The Strategy header shows the working status and every Strategy action disables; the new set replaces the panel's cards and **Latest analysis** shows the run's answer.
| **Get topic ideas**           | `POST /runs` with the trend trigger                         | A synthesis focused on the trend replaces the Strategy panel's set.                                                                                                                                                          |
| **Draft outreach**            | `POST /runs` with the influencer trigger                    | Execution returns an outreach deliverable in the transcript.                                                                                                                                                    |
| **Do this**                   | none                                                        | The recommendation's request is written into the Execution composer and is not sent automatically. No run is created until the marketer presses **Send**; sent unedited, it runs that recommendation (`RECOMMENDATION` `DO_THIS`), and an edited request goes to the router as chat.                                                       |
| Approve                       | `POST /actions/{id}/approve`                                | Shows `Approving…`, then `EXECUTED` and the receipt, or `FAILED` with its `error`.                                                                                                                              |
| Simulate                      | `POST /activities/simulate`                                 | The new card arrives through `activity.created`, not the POST response.                                                                                                                                         |
| Feed at top for 2 s           | `POST /activities/mark-seen`                                | `NEW` dots fade and the unseen count resets.                                                                                                                                                                    |
| Tracking keyword save         | `PUT /company/tracked-keywords`                             | The editor shows the validated, canonical list; the competitor feed is unchanged.                                                                                                                               |

On load, restore `localStorage.session_id` through `GET /sessions/{id}` and
open the activity SSE plus any `RUNNING` run stream.

## 5. States

Every data region implements loading, empty and error states. Copy is direct
and useful: never apologize, and render enum values verbatim.

| Region           | Loading                                  | Empty                                                                                  | Error                                                                         |
| ---------------- | ---------------------------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Social listening | 5 keyword/trend/influencer skeleton rows | `No trends computed yet.` or `No influencers matched these keywords.`                  | API `message` verbatim plus **Retry**                                         |
| Activity feed    | 4 flat skeleton cards                    | `No competitor activity in the last 30 days — run the pipelines or simulate a signal.` | API `message` verbatim plus **Retry**                                         |
| Strategy panel   | 3 recommendation skeleton rows           | `No strategy yet. Generate strategy to get the team's plays.`                                 | API `message` verbatim plus **Retry**                                         |
| Execution chat   | Run progress checklist                   | `Pick an item from the feed, or ask Execution for a deliverable.`; 3 prompt chips above the composer | `run.failed` message verbatim plus **Retry run**                              |
| SSE connection   | —                                        | —                                                                                      | Thin warning bar: `Live updates paused — reconnecting…`, with bounded backoff |

## 6. Accessibility

- All interactive controls are keyboard-reachable with a visible 2px focus
  ring using `--border-focus`.
- The run progress and live feed inserts use `aria-live="polite"`; new items
  are announced as `New competitor activity: …`.
- Color is never the only signal: badges carry text and momentum has an arrow
  and sign.
- Text meets WCAG AA contrast, checked by an axe scan in the Playwright suite.
  The design system's status fills (`--color-secondary`, `--color-success`,
  `--color-warning`) reach only 2.3:1 to 3.3:1 as type on a light surface, so
  status **text** uses the darker `--color-text-favorable`,
  `--color-text-attention` and `--color-text-unfavorable` tokens, which clear
  4.5:1 on white, on the page ground and on their own tints. The fill tokens
  are unchanged and still carry badges, dots and borders.
- The dark theme meets the same bar. Its values come from the design canvas's
  dark board, lightened where the canvas missed AA: status text, red type
  (`--color-text-accent`) and the TopBar's muted text on the red band. Filled
  buttons keep `--color-primary-hover` in both themes. The axe scan runs in
  both themes.
- Enum badges use the 12px uppercase label style, and an enum is never
  re-cased for display: a lowercase value such as `schedule_social_post`
  renders as itself.
- The keyword editor labels every input and exposes validation text without
  relying on color.

## 7. Deliberate deviations from the design system

| Design-system rule                              | Deviation                                                                         | Why                                                                                                                                                                                                |
| ----------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fixed 240px left sidebar with company selector  | No sidebar; the tenant selector is in the TopBar.                                 | The PoC has one tenant and needs the space for social listening.                                                                                                                                   |
| Nothing is sticky except the sidebar and TopBar | The Execution composer is docked at the bottom of its fixed-height transcript.    | It must remain reachable while a long turn is visible.                                                                                                                                             |
| Max content width ~1100px, single column        | Full-width three-region workspace, capped at 320/flex/360.                        | Watching, deciding and acting are simultaneous jobs.                                                                                                                                               |
| `--color-primary` fills the primary button      | Filled buttons use `--color-primary-hover` and press to `--color-primary-strong`. | White on `--color-primary` is 4.32:1, below the AA 4.5:1 that §6 requires. `--color-primary` is unchanged and still carries every accent that is not type on a fill, and no longer sets 13px type. |
| Inter at 13/15/18/24/32px, weight 600 | Geist at 11/12/13/14/16px, weight 500. | The owner's redesigned workspace canvas sets a quieter, denser scale for a three-region screen. |
| Light only | A dark theme remapping the same tokens; the TopBar band turns brand red. | The owner's canvas adds a dark board. |

## 8. Anti-slop checklist

The build fails review if any item fails.

- [ ] No gradients, glassmorphism, blur, glow, textured backgrounds or
      illustrations.
- [ ] No emoji except 🧪 (`SIMULATED`) and 🎭 (`Simulate`).
- [ ] Agent output uses structured blocks, never chat bubbles; only marketer
      messages may use a quiet bubble.
- [ ] No placeholder avatars, stock imagery or lorem ipsum, including seed
      data.
- [ ] No AI-sparkle iconography or labels such as `✨ Generate with AI`.
- [ ] One primary button per card; all other controls are secondary or quiet.
- [ ] Colors, spacing, radius, shadow and type use only the tokens in
      `frontend/src/styles/theme.css`; no arbitrary values, inline styles or
      literal colours in any component.
- [ ] Spacing follows the 8px grid (4px half-steps allowed) and type uses
      only the five sizes in `theme.css`.
- [ ] Both themes are checked: every region reads in light and dark, and the
      axe scan passes in each.
- [ ] Enums render verbatim (`NEW_BLOG`, not `New blog post`).
- [ ] Numbers are tabular and concrete (`$2,500 → $1,990`, `▲142%`).
- [ ] No spinner appears without a text label, and motion stays within DS
      tokens plus the evidence flash.
- [ ] Every mock or simulated record is badged.
- [ ] Every region has loading, empty and error states from §5.
