# UI Specification — Single-Page Marketing Workspace

> Parent: [specs.md](specs.md) · API: [api-contract.md](api-contract.md)
> Design system: **CompetitorScope Design System**
> (`../Competitors-Monitoring/design/CompetitorScope Design System/`). Its
> `readme.md` is binding for color, type, spacing, shape, motion, iconography
> and content voice. This document covers the page-specific workspace and its
> deliberate deviations from that system.

## 1. Principles

1. **One page, three jobs.** Social listening is on the left, Execution chat
   is in the centre, and Strategy plus competitor evidence is on the right.
   There is no route change for these jobs.
2. **Execution owns the conversation.** The centre transcript belongs to the
   Execution agent, and there is nothing in it to route elsewhere: the
   composer has no agent selector. Strategy recommendations stay in their own
   panel and are handed to Execution through an explicit user action, and
   Strategy runs are started from a feed item, a trend or an influencer.
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
│ TopBar: [Marketing Eye ▾]  Marketing workspace  Last sync 3 min ago  [🎭 Simulate ▾]     │
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
       320px fixed                         flex                         360px fixed
```

- The page ground is `--surface-page`. The three working regions are white
  panels with a 1px border. Gutters are 16px and page padding is 24px. At the
  1440×900 design target the grid is `320px / minmax(560px, 1fr) / 360px`: the
  right rail stacks Strategy over the feed and needs the extra width, while the
  left rail holds a keyword editor and two compact tables.
- The left region contains tracking keywords, trends and influencers. The
  right region puts Strategy recommendations above the competitor activity
  feed. The centre region is the only chat transcript.
- Each region scrolls independently. The TopBar is sticky. The Execution
  composer is docked to the bottom of the centre transcript.
- The TopBar has no logo. It contains the tenant selector, context label, last
  sync time and the Simulate menu.
- **Responsive:**
  - At 1280px and below, the left social-listening region becomes a tab in the
    workspace shell while Strategy and the feed remain available.
  - At 900px and below, the page is one column with a bottom segmented switcher
    `Feed | Workspace | Insights`.
  - At every width, the body never scrolls horizontally.

## 3. Components

Components are rebuilt as Tailwind components in
`frontend/src/components/ds/`, using only token utilities from
`frontend/src/styles/theme.css` (see
[coding-conventions.md §6](coding-conventions.md#6-frontend-react-vite-and-tailwind)).

| Component              | Built from                  | Notes                                                                                                                                                                                                                                                                                                                                                           |
| ---------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TopBar`               | DS controls                 | Tenant selector, `Marketing workspace` context label, last-sync meta text and Simulate menu. No logo.                                                                                                                                                                                                                                                           |
| `SimulateMenu`         | DS `Button` + overlay       | Lists all 9 `ActivityType` values plus `Random`; shows a labelled `Simulating…` state while the request is in flight.                                                                                                                                                                                                                                           |
| `SocialListeningPanel` | DS `Card`, `Input`, `Tabs`  | Tracking-keyword editor in the header, then Trends and Influencers panels. Keywords scope social listening only; they do not filter the competitor feed.                                                                                                                                                                                                        |
| `TrackedKeywordEditor` | DS `Input` + quiet controls | Shows five seeded terms, trims on save, rejects empty values, and enforces 1–20 case-insensitively unique terms.                                                                                                                                                                                                                                                |
| `TrendRow`             | DS row primitives           | Topic, channel, momentum with arrow and sign, mention count, sample-post links and a **Get topic ideas** quiet button.                                                                                                                                                                                                                                          |
| `InfluencerTable`      | DS table                    | Exactly two visible columns: Influencer and Followers. Each row shows a monogram, linked handle, channel, compact followers, engagement and up to three topic labels, plus **Draft outreach**. No avatar images.                                                                                                                                                |
| `ExecutionChat`        | DS `Card`, `Input`          | Fixed-height, independently scrolling transcript. The composer is docked beneath it and offers an auto-growing textarea (max 6 lines) and **Send**. There is no agent selector: the centre belongs to the Execution agent alone, Strategy is reached from a feed item, and a strategy-shaped message comes back as one clarification line pointing at the feed. |
| `ExecutionTurn`        | Structured blocks           | Shows the `EXECUTION` label and trigger, one collapsed line for thinking/tool calls that expands to reasoning and one row per tool, then the answer and deliverable block. Only marketer messages may use a quiet bubble.                                                                                                                                       |
| `DeliverableCard`      | DS `Card`                   | Type, channel, title, sanitized markdown body, word/character count, **Copy**, variants, four quality statuses and proposed-action controls.                                                                                                                                                                                                                    |
| `ProposedActionRow`    | DS buttons                  | Editable schedule (`scheduled_for` for social posts, `date` for calendar entries), **Discard** and **Approve**. Approval ends with `EXECUTED`, receipt ID and `mock`, or a terminal `FAILED` row showing `error`.                                                                                                                                               |
| `ClarificationBlock`   | DS secondary buttons        | One clarification line with 2–3 quick replies. A Strategy-shaped question points at the feed instead of entering the Execution transcript.                                                                                                                                                                                                                      |
| `StrategyPanel`        | DS rows + sheet             | Recommendation rows show ordinal, priority, decision at body weight 600, status and plain-language `next_action`.                                                                                                                                                                                                                                               |
| `RecommendationSheet`  | DS pop-out sheet            | 440px wide. Shows what to do, why, evidence chips and **Do this**. Clicking **Do this** writes the request into the Execution composer without sending it.                                                                                                                                                                                                      |
| `EvidenceChip`         | DS pill                     | Displays a short title and keeps the raw evidence ID in a tooltip. Click scrolls to and flash-highlights the target item.                                                                                                                                                                                                                                       |
| `ActivityFeed`         | DS `Card`, `EmptyState`     | Header, unseen count, type and competitor filters, newest-first cursor pagination, live inserts and seen state. Lives below Strategy on the right.                                                                                                                                                                                                              |
| `ActivityCard`         | DS `Card`, badges           | Type, relative time, competitor/channel, two-line title, conditional author or price delta, safe external URL, primary action from `actions[]`, quiet secondary action, and `MOCK`/`🧪 SIMULATED` badges.                                                                                                                                                       |
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
| **Get topic ideas**           | `POST /runs` with the trend trigger                         | Strategy recommendations appear in the Strategy panel.                                                                                                                                                          |
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
| Strategy panel   | 3 recommendation skeleton rows           | `No open recommendations — ask Strategy for a plan.`                                   | API `message` verbatim plus **Retry**                                         |
| Execution chat   | Run progress checklist                   | `Pick an item from the feed, or ask Execution for a deliverable.` with 3 prompt chips  | `run.failed` message verbatim plus **Retry run**                              |
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
- Enum badges use the 13px uppercase label style, and an enum is never
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
      `frontend/src/styles/theme.css`; no arbitrary values or inline styles.
- [ ] Spacing follows the 8px grid and type uses only the five DS sizes.
- [ ] Enums render verbatim (`NEW_BLOG`, not `New blog post`).
- [ ] Numbers are tabular and concrete (`$2,500 → $1,990`, `▲142%`).
- [ ] No spinner appears without a text label, and motion stays within DS
      tokens plus the evidence flash.
- [ ] Every mock or simulated record is badged.
- [ ] Every region has loading, empty and error states from §5.
