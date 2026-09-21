# UI Specification — Single-Page Marketing Workspace

> Parent: [specs.md](specs.md) · API: [api-contract.md](api-contract.md)
> Design system: **CompetitorScope Design System**
> (`../Competitors-Monitoring/design/CompetitorScope Design System/`). Its
> `readme.md` is binding for color, type, spacing, shape, motion, iconography
> and content voice. This document covers only what is specific to this page,
> and the deliberate deviations from the design system.

---

## 1. Principles

1. **One page, three jobs.** Watch (feed), decide and act (workspace), and
   explore (insights). No routing and no modals, except the Simulate menu and
   the action-approval confirmation.
2. **An instrument, not a chatbot.** Agent output renders as structured cards
   (recommendations, deliverables, actions). Chat bubbles are not the main
   surface. The chat composer is an input, not the centrepiece.
3. **Every button says where it goes.** Buttons are labelled with the outcome
   ("Draft a CEO post"). The run header names the agent that answered and
   the reason it was chosen.
4. **Evidence is clickable.** Every evidence chip scrolls to and highlights
   its feed item or insight row.
5. **Design-system discipline.** There is one primary button per card, flat
   cards, the 8px grid, enums shown verbatim, and no decorative emoji (only
   🧪 SIMULATED and 🎭 Simulate).

## 2. Layout

The design target is 1440×900.

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ TopBar: [RM wordmark] Marketing workspace · Marketing Eye      Last sync 3 min ago  [🎭 Simulate a signal ▾] │
├─────────────────────────┬──────────────────────────────────────────────┬─────────────────┤
│ COMPETITOR ACTIVITY  3 new│  WORKSPACE                                   │ [Trends|Influencers|Topics] │
│ [All types ▾][All comps ▾]│                                              │                 │
│ ┌─────────────────────┐ │  ┌ Run · STRATEGY · Why it matters ─────────┐ │ AI search (GEO) │
│ │● NEW  EXECUTIVE_POST│ │  │ Routed: button "Why it matters"          │ │ LINKEDIN ▲142%  │
│ │Brightlane · LinkedIn│ │  │ ✓ Loading company context                │ │ 412 mentions    │
│ │"Agencies that still │ │  │ ✓ Searching competitor activity (4)      │ │ [Get topic ideas]│
│ │ bill hourly…"        │ │  │ ◌ Loading skill: content-strategy        │ │ ─────────────── │
│ │by Dana Reyes, CEO    │ │  └──────────────────────────────────────────┘ │ …               │
│ │brightlane.example/…↗ │ │  ┌ Recommendation 1 · HIGH · CONTENT_TOPIC ─┐ │                 │
│ │2 min ago  🧪SIMULATED│ │  │ Title …                                  │ │                 │
│ │[Draft a CEO post]    │ │  │ Rationale …                              │ │                 │
│ │ Why it matters       │ │  │ [act_…][trd_…]           [Do this]       │ │                 │
│ └─────────────────────┘ │  └──────────────────────────────────────────┘ │                 │
│ ┌─────────────────────┐ │  ┌ Deliverable · CEO_POST · LinkedIn ───────┐ │                 │
│ │ NEW_BLOG            │ │  │ body…  [Copy]                            │ │                 │
│ │Lyfe Marketing · Web │ │  │ Quality check: PASS PASS FIXED PASS      │ │                 │
│ │"7 B2B Content…"      │ │  │ Proposed: Schedule on LinkedIn · Tue 9:00│ │                 │
│ │lyfemarketing.com/…↗  │ │  │                     [Discard] [Approve]  │ │                 │
│ │[Create a similar blog]│ │  └──────────────────────────────────────────┘ │                 │
│ └─────────────────────┘ │ ┌──────────────────────────────────────────┐ │                 │
│  … (infinite scroll)    │ │ [Auto|Strategy|Execution]                │ │                 │
│                         │ │ Ask for a plan or a deliverable…   [Send]│ │                 │
│                         │ └──────────────────────────────────────────┘ │                 │
└─────────────────────────┴──────────────────────────────────────────────┴─────────────────┘
      360px fixed                    flex (min 560px)                       320px fixed
```

- The page ground is `--surface-page`. The columns are white panels with a 1px
  border. Gutters are 16px, and the page padding is 24px.
- Each column scrolls independently. The TopBar and the chat composer are
  sticky (a deliberate deviation, see §7).
- **Responsive:**
  - 1280px and below: the insights rail collapses into a fourth tab in the
    workspace header.
  - 900px and below: a single column, with a bottom segmented switcher
    `Feed | Workspace | Insights`.
  - At every width, the page body never scrolls horizontally.

## 3. Components

New components are built from design-system primitives. The design-system
`.jsx` components are rebuilt as Tailwind components in
`frontend/src/components/ds/`, keeping their props and using only the token
utilities from `src/styles/theme.css` (see
[coding-conventions.md §6](coding-conventions.md#6-frontend-react-vite-and-tailwind)).

| Component | Built from | Notes |
|---|---|---|
| `TopBar` | DS `TopBar` | Wordmark, page title, the company name (static; there's one tenant), "Last sync …" (meta text) and the Simulate menu button |
| `SimulateMenu` | DS `Button` + overlay | 🎭 Simulate a signal ▾ opens a list of the 9 `ActivityType` enums plus "Random". While the request is in flight the button shows a spinner and the label "Simulating…". |
| `ActivityFeed` | DS `Card`, `EmptyState` | Header: "Competitor activity", an unseen count pill, and two `Select` filters (type, competitor). Newest first. Infinite scroll by cursor. |
| `ActivityCard` | DS `Card`, `ActivityTypeBadge`, `SimulatedBadge` | Row 1: `NEW` dot (unseen), type badge, relative time. Row 2: competitor name · channel. Row 3: title (2-line clamp). Then author (for `EXECUTIVE_POST`), `PriceDelta` (for `PRICE_CHANGE`/`PROMOTION`) and the URL (domain + path, truncated, external-link icon, `target=_blank rel=noopener`). Footer: the primary action button (from `actions[]`) and the secondary as a quiet link-button. A MOCK or 🧪 SIMULATED badge appears when flagged. |
| `ActivityTypeBadge` | DS `ChangeTypeBadge` | Extends the DS enum set. The five CompetitorScope types keep their DS tones. `SOCIAL_POST`, `EXECUTIVE_POST`, `CAMPAIGN_LAUNCH` and `PROMOTION` use the muted tone. No new colors. |
| `MockBadge` | DS `StatusBadge` (muted) | Label `MOCK`, with tooltip "Demo data — not a detected change". |
| `Workspace` | — | A vertical list of `RunBlock`s for the session, oldest first. It auto-scrolls to a new run only when the user is already near the bottom. |
| `RunBlock` | DS `Card` | Header: an agent pill (`STRATEGY`/`EXECUTION`), the intent enum, the route reason (meta text) and the elapsed time. Body: `RunProgress` while running, then the output cards. |
| `RunProgress` | — | Checklist of `agent.step` labels (✓ done, spinner for the current step). "Show trace" expands the `agent.tool` rows (tool, args summary, count, ms). |
| `AnswerBlock` | — | `answer`, and `implications` as a numbered list. `assumptions` and `data_gaps` sit in a quiet disclosure: "Assumptions & data gaps (n)". |
| `RecommendationCard` | DS `Card` | Ordinal + priority badge + kind enum, title (h3), rationale, evidence chips, skills used (meta), and a primary **Do this** button (when `next_action` is present) → `POST /runs` with a `RECOMMENDATION` trigger |
| `EvidenceChip` | DS pill | The label is the short title of the evidence record, not the raw ID. The ID shows in a tooltip. Click → scroll and flash-highlight the target (a 1.2 s background tint; the only highlight motion on the page). |
| `DeliverableCard` | DS `Card` | Type enum + channel, title, the rendered markdown body (a sanitized renderer), word/char count against the channel limit, a **Copy** button, `variants` as tabs, and a `QualityCheckRow` (4 status badges: PASS=success, FIXED=warning, FLAG=error, with a notes disclosure) |
| `ProposedActionRow` | DS `Button` ×2 | Summary text, editable `scheduled_for` for social posts (datetime input), **Discard** (secondary) and **Approve** (primary). After approval: an `EXECUTED` status badge, the receipt ID and a `mock` label. |
| `ClarificationBlock` | DS `Button` (secondary) | The question, plus 2–3 quick-reply chips. Clicking one sends it as the next message. |
| `RefusalBlock` | — | The reason plus the offered alternative. Neutral tone (muted), not error red. |
| `ChatComposer` | DS `SegmentedSwitcher`, `Input` | Agent selector `Auto | Strategy | Execution`, an auto-growing textarea (max 6 lines), and **Send** (primary). Enter sends; Shift+Enter adds a newline. Disabled while a run in this session is streaming, with the label "Waiting for the current run…". |
| `InsightsRail` | DS text tabs | Tabs: `Trends`, `Influencers`, `Topics`. The active tab has a 2px brand-red underline. |
| `TrendRow` | — | Topic (h3-weight 15px), channel enum, `▲142%` momentum (tabular figures; RISING=favorable, FALLING=unfavorable, STEADY=muted), mention count, 1–2 sample post links, and a **Get topic ideas** quiet button |
| `InfluencerRow` | — | Name, handle, channel, followers (compact, e.g. `48.2K`), engagement %, topics (≤ 3), and a **Draft outreach** quiet button. No avatar images. |
| `TopicRow` | — | Open recommendations: ordinal, title, priority and **Do this** |

## 4. Interaction flows

| Trigger | Request | Immediate UI response |
|---|---|---|
| Feed primary/secondary button | `POST /runs {trigger: {kind: FEED_ACTION, ref_id, action}}` | A new `RunBlock` appears at the bottom of the workspace with the header filled in. The source card shows a quiet "Sent to workspace" note for 2 s. The workspace scrolls to the run. |
| Chat send | `POST /runs {message, agent_hint}` | The user's message renders as a quiet right-aligned line above a new `RunBlock`. If the response is `200` (clarify or out-of-scope), a `ClarificationBlock` or `RefusalBlock` renders with no run. |
| Do this / Get topic ideas / Draft outreach | `POST /runs` with the matching trigger | Same as a feed button |
| Approve | `POST /actions/{id}/approve` | The button shows a spinner and "Approving…", then an `EXECUTED` badge and the receipt |
| Simulate | `POST /activities/simulate` | The new card arrives through the `activity.created` SSE event, not through the POST response, so the live path is what's demonstrated |
| Feed scrolled to top for 2 s | `POST /activities/mark-seen` | `NEW` dots fade after 1 s and the unseen count pill resets |

When the page loads, the UI restores the session (`localStorage.session_id` →
`GET /sessions/{id}`) and opens both SSE streams (the activity stream and any
`RUNNING` run).

## 5. States

Every data region implements every state below. Copy follows the design-system
voice: direction, not mood; never apologize; enums verbatim.

| Region | Loading | Empty | Error |
|---|---|---|---|
| Feed | 4 skeleton cards (flat grey blocks, no shimmer) | "No competitor activity in the last 30 days — run the pipelines or simulate a signal." | The API `message` verbatim, plus **Retry** |
| Workspace | — | "Pick an item from the feed, or ask for a plan or a deliverable below." with 3 example prompt chips | The `run.failed` message verbatim inside the `RunBlock`, plus **Retry run** |
| Trends / Influencers / Topics | 5 skeleton rows | Trends: "No trends computed yet." Topics: "No open recommendations — ask the Strategy agent for topic ideas." | Verbatim + Retry |
| SSE disconnect | — | — | A thin bar under the TopBar: "Live updates paused — reconnecting…" (warning tone). It auto-retries with backoff. |

## 6. Accessibility

- All interactive elements are keyboard-reachable, with a visible focus ring
  (2px `--border-focus`).
- `RunProgress` is an `aria-live="polite"` region, and new feed items are
  announced ("New competitor activity: …").
- Color is never the only signal: badges carry text, and momentum has an
  arrow and a sign.
- Text meets WCAG AA contrast. Enum badges use the 13px uppercase label
  style.

## 7. Deliberate deviations from the design system

| Design-system rule | Deviation | Why |
|---|---|---|
| Fixed 240px left sidebar with the company selector | **No sidebar.** The company name is in the TopBar. | One page with one tenant, so navigation would be empty. The width goes to the three working columns. |
| "Nothing is sticky except the sidebar and TopBar" | The chat composer is sticky at the bottom of the workspace column | The composer must stay reachable while long outputs scroll |
| Max content width ~1100px, single column | Full-width, three columns | The workspace layout is the product. The columns cap at 360/flex/320. |

## 8. Anti-slop checklist

The build fails review if any item fails.

- [ ] No gradients, glassmorphism, blur, glow, textured backgrounds or illustrations.
- [ ] No emoji except 🧪 (SIMULATED) and 🎭 (Simulate).
- [ ] No chat-bubble UI for agent output. Structured cards only.
- [ ] No placeholder avatars, stock imagery or lorem ipsum anywhere, including seed data.
- [ ] No "AI sparkle" iconography or labels like "✨ Generate with AI". Buttons name outcomes.
- [ ] One primary button per card. All other buttons are secondary or quiet.
- [ ] Only design-system tokens are used for color, spacing, radius, shadow and type, through the Tailwind theme in `src/styles/theme.css`. No arbitrary values or inline styles (ESLint rule).
- [ ] Spacing is on the 8px grid only. Type uses only the 5 DS sizes.
- [ ] Enums render verbatim (`NEW_BLOG`, not "New blog post").
- [ ] Numbers are tabular and concrete (`$2,500 → $1,990`, `▲142%`), never adjectives.
- [ ] No spinner without a text label. No animation beyond DS motion tokens and the evidence flash.
- [ ] Every mock or simulated record is badged.
- [ ] Every region has loading, empty and error states (§5).
