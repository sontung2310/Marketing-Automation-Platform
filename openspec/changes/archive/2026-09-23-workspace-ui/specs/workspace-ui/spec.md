# Spec Delta

## Purpose

Provides the marketing manager one page that watches the market, decides
what to do and produces the deliverable, with every agent claim traceable to
a clickable piece of evidence.

## ADDED Requirements

### Requirement: The workspace renders three regions on one page

The page SHALL render, without a route change, a sticky inverted TopBar over
three independently scrolling regions: social listening on the left,
the Execution transcript in the centre, and Strategy recommendations above
the competitor activity feed on the right. At the 1440×900 design target the
grid SHALL be `320px / minmax(560px, 1fr) / 360px` with 16px gutters and
24px page padding. The TopBar SHALL carry the tenant selector, the
`Marketing workspace` context label, the last-sync time and the Simulate
menu, and SHALL carry no logo. Every color, spacing, radius, shadow and type
value SHALL come from a token in `frontend/src/styles/theme.css`; no
component may use an inline `style` attribute or a Tailwind arbitrary value.

#### Scenario: The seeded workspace loads at the design target

- **GIVEN** typed fixtures for the seeded company, feed, trends,
  influencers and agent streams
- **WHEN** the page loads at 1440×900
- **THEN** the left social-listening region, the centre Execution empty
  state and the right Strategy and feed regions all render, the tenant
  selector, the five tracking keywords and the last-sync label are visible,
  no console error is logged, and an axe accessibility scan reports no
  violation

#### Scenario: The layout collapses at the documented breakpoints

- **GIVEN** the workspace is open
- **WHEN** the viewport narrows to 900px
- **THEN** the page becomes one column with a bottom segmented
  `Feed | Workspace | Insights` switcher, and the body never scrolls
  horizontally at any width

### Requirement: Every feed item offers its type's mapped action

Each activity card SHALL render its `activity_type` and channel verbatim,
a relative detected time, the competitor name, a two-line title, a safe
external link, and the primary and secondary buttons from the item's
server-computed `actions[]`. The UI SHALL hold no mapping from activity type
to action. A `PRICE_CHANGE` or `PROMOTION` card SHALL show its price as
`before → after` with the signed delta; an `EXECUTIVE_POST` card SHALL show
the author name and role; and any record with `is_mock` or `is_simulated`
SHALL carry the corresponding badge.

#### Scenario: Each activity type renders its mapped primary action

- **GIVEN** one fixture card for each of the nine `ActivityType` values
- **WHEN** each card renders
- **THEN** it shows the primary action from `docs/specs.md` §6, a
  `PRICE_CHANGE` card shows `before → after`, an `EXECUTIVE_POST` card shows
  its author and role, and mock and simulated items are badged

#### Scenario: New activity arrives over the stream

- **GIVEN** the feed is subscribed to the activity stream
- **WHEN** an `activity.created` event arrives
- **THEN** the item is inserted at the top of the feed with a `NEW` marker,
  the unseen count increases, and the insert is announced through a polite
  live region

### Requirement: Tracked keywords scope social listening only

The listening panel SHALL show the company's tracked keywords and let the
marketer edit them. The editor SHALL trim each term, reject empty terms,
enforce 1–20 terms unique case-insensitively, and show the canonical list
the API returns. Saving keywords SHALL NOT change the competitor feed's
filters or contents.

#### Scenario: A duplicate keyword is rejected without color as the only signal

- **GIVEN** the keyword editor holds the five seeded terms
- **WHEN** the marketer adds a term that repeats an existing one in a
  different case
- **THEN** the editor shows the validation message as text, the list is
  unchanged, and no request is sent

### Requirement: The Execution transcript streams one structured turn per run

The centre region SHALL be a fixed-height, independently scrolling
transcript with the composer docked beneath it. Only the marketer's messages
SHALL use a bubble. Each agent turn SHALL render the `EXECUTION` label and
its trigger, one collapsed line covering thinking and tool calls that
expands into the reasoning and one row per tool, the answer, and, when
present, the deliverable block with its type, channel, title, word count,
four quality-check statuses and proposed actions. The composer SHALL offer
`Auto | Strategy | Execution`, an auto-growing textarea and **Send**. A run
SHALL never leave the transcript without a visible update for more than 10
seconds, and no spinner SHALL appear without a text label.

#### Scenario: A streaming run fills the transcript

- **GIVEN** an Execution run fixture streaming its events
- **WHEN** the run progresses from `run.started` to `run.completed`
- **THEN** the transcript shows the labelled trigger, the collapsed
  thinking and tool line, each progress step, the answer and the
  deliverable, only marketer messages use bubbles, and no silent gap exceeds
  10 seconds

#### Scenario: A proposed action is approved

- **GIVEN** a turn whose deliverable carries a `PROPOSED` action
- **WHEN** the marketer approves it
- **THEN** the row shows a labelled in-flight state, then `EXECUTED`, the
  mock receipt ID and the `mock` label, and the approve control is no longer
  offered

#### Scenario: The session is restored after a refresh

- **GIVEN** a session ID in `localStorage` and a completed run
- **WHEN** the page reloads
- **THEN** the transcript is rebuilt from the session's runs, oldest first,
  and any `RUNNING` run reattaches to its event stream

### Requirement: Strategy output stays in its own panel and reaches Execution by an explicit action

Strategy recommendations SHALL never enter the Execution transcript. Each
recommendation SHALL render as a compact row grouped under the run that
produced it, showing its ordinal, priority, the decision at body weight 600,
its status and its `next_action` in plain words. Opening a row SHALL open a
440px sheet with what to do, why, evidence chips and **Do this**. **Do this**
SHALL write the recommendation's brief into the Execution composer and SHALL
NOT start a run. An evidence chip SHALL show a short title, keep its raw
evidence ID in its tooltip, and on activation scroll to and flash-highlight
its target item.

#### Scenario: Do this prefills the composer without sending

- **GIVEN** Strategy recommendations in the fixture
- **WHEN** the marketer opens a recommendation and clicks **Do this**
- **THEN** the 440px sheet showed the decision, rationale and evidence, the
  recommendation's request is in the Execution composer, and no run was
  created

#### Scenario: An evidence chip navigates to its source

- **GIVEN** an open recommendation sheet citing a feed item
- **WHEN** the marketer activates that evidence chip
- **THEN** the feed scrolls to the cited item and flash-highlights it

### Requirement: Every region degrades independently

Every data region SHALL implement a loading, an empty and an error state. An
error state SHALL render the API error envelope's `message` verbatim
alongside a **Retry** control, and SHALL NOT prevent the other regions from
working. A dropped event stream SHALL show the reconnecting warning bar and
retry with bounded backoff.

#### Scenario: One region fails while the rest keep working

- **GIVEN** the workspace is open
- **WHEN** one region's endpoint returns `503` with an error envelope
- **THEN** that region shows the envelope's `message` verbatim with
  **Retry**, and every other region stays usable
