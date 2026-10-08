# workspace-ui Specification

## Purpose
Provides the marketing manager one page that watches the market, decides
what to do and produces the deliverable, with every agent claim traceable to
a clickable piece of evidence.

## Requirements

### Requirement: The workspace renders three regions on one page

The page SHALL render, without a route change, a sticky TopBar over three
independently scrolling regions: social listening on the left, the Execution
transcript in the centre, and Strategy recommendations above the competitor
activity feed on the right. At the 1440×900 design target the grid SHALL be
`320px / minmax(0, 1fr) / 425px` with 16px gutters and 24px page
padding, so the centre absorbs the width and the body never scrolls
horizontally down to the 1281px desktop breakpoint. The TopBar SHALL carry the tenant selector, the `Marketing workspace`
context label, the last-sync time, the theme menu and the Simulate menu, and
SHALL carry no logo. Each panel header SHALL show an icon, the panel title and
a count or status pill. Every color, spacing, radius, shadow and type value
SHALL come from a token in `frontend/src/styles/theme.css`, type SHALL use only
that file's five sizes, and no component may use an inline `style` attribute,
a Tailwind arbitrary value or a literal color.

#### Scenario: The seeded workspace loads at the design target

- **GIVEN** typed fixtures for the seeded company, feed, trends,
  influencers and agent streams
- **WHEN** the page loads at 1440×900
- **THEN** the left social-listening region, the centre Execution empty
  state and the right Strategy and feed regions all render, the right region
  is 425px wide, every panel header shows its icon, title and pill, the
  tenant selector, the five tracking keywords and the last-sync label are
  visible, no console error is logged, and an axe accessibility scan reports
  no violation

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

The listening panel SHALL show the company's tracked keywords as a list, one
row per term, with a labelled remove control that is visible on row hover or
keyboard focus and an **Add keyword** control. The editor SHALL trim each term,
reject empty terms, enforce 1–20 terms unique case-insensitively, and show the
canonical list the API returns. Saving keywords SHALL NOT change the
competitor feed's filters or contents. The trend platform filter SHALL be a
segmented control whose options each show the number of trends they hold.

#### Scenario: A duplicate keyword is rejected without color as the only signal

- **GIVEN** the keyword editor holds the five seeded terms
- **WHEN** the marketer adds a term that repeats an existing one in a
  different case
- **THEN** the editor shows the validation message as text, the list is
  unchanged, and no request is sent

#### Scenario: A keyword is removed from the keyboard

- **GIVEN** the keyword list holds the five seeded terms
- **WHEN** the marketer tabs to a row's remove control and activates it
- **THEN** the control is visible while focused, and the saved list no
  longer holds that term

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

Strategy recommendations SHALL never enter the Execution transcript. The
Strategy panel header SHALL carry a **Generate strategy** button that starts
a run with the `COMPANY` `GENERATE_STRATEGY` trigger. While any Strategy run
is in flight, the header SHALL show a labelled working status and every
control that starts a Strategy run (**Generate strategy**, and each item
action whose agent is Strategy, such as **Plan a response**, **Why it
matters** and **Get topic ideas**) SHALL be disabled, so only one Strategy
run is in flight at a time (owner decision, 2026-10-08). The panel SHALL show
only the company's `OPEN` recommendations and SHALL refresh when a run
completes. Above the cards, a **Latest analysis** block SHALL show the
latest successful Strategy run started on the page: its answer, its
implications and its data gaps, so an analysis without recommendations (such
as **Why it matters**) is still visible (owner decision, 2026-10-08). Each
recommendation SHALL render as a card showing its zero-padded ordinal, its
priority verbatim, its title, its `insight`, its `audience`, up to three
signal lines drawn from its evidence (each labelled `Trend`, `Competitor`,
`Influencer` or `Company` with the evidence note), and
an **Open plan** button that names the recommendation in its accessible name.
The panel header SHALL count the recommendations shown. **Open plan** SHALL
open a 520px sheet with the insight and the audience, what to make, the
channel, why, the evidence chips under `Based on`, and **Do this**. **Do
this** SHALL write the
recommendation's brief into the Execution composer and SHALL NOT start a run.
When the marketer sends that brief unedited, the run SHALL start from the
`RECOMMENDATION` `DO_THIS` trigger, so Execution receives that recommendation;
an edited brief SHALL be sent as a chat message. An evidence chip SHALL show
its kind and a short title, keep its raw evidence ID in its tooltip, and on
activation scroll to and flash-highlight its target item.

#### Scenario: Do this prefills the composer without sending

- **GIVEN** Strategy recommendations in the fixture
- **WHEN** the marketer clicks a card's **Open plan** and then **Do this**
- **THEN** the 520px sheet showed the insight, audience, decision, rationale
  and evidence, the recommendation's request is in the Execution composer,
  and no run was created

#### Scenario: A recommendation card summarises its signals

- **GIVEN** a recommendation citing one trend and one activity
- **WHEN** the Strategy panel renders
- **THEN** its card shows the zero-padded ordinal, the verbatim priority, the
  title, the insight, the audience, a `Trend` line and a `Competitor` line
  with their notes, and an **Open plan** button

#### Scenario: Why it matters shows its analysis without cards

- **GIVEN** the panel shows recommendations from an earlier run
- **WHEN** the marketer clicks **Why it matters** on a feed card and the run
  completes with implications and no recommendations
- **THEN** the **Latest analysis** block shows the run's answer and
  implications, and the earlier recommendation cards are unchanged

#### Scenario: Strategy actions are disabled while a Strategy run is in flight

- **GIVEN** a Strategy run in flight
- **WHEN** the workspace renders
- **THEN** **Generate strategy** and every Strategy item action in the feed
  and the Trends list are disabled, while Execution actions stay enabled

#### Scenario: Generate strategy replaces the panel's set

- **GIVEN** the panel shows recommendations from an earlier run
- **WHEN** the marketer clicks **Generate strategy** and the run completes
- **THEN** the button was disabled with a working status during the run,
  and the panel then shows only the new run's recommendations

#### Scenario: Sending the unedited brief runs that recommendation

- **GIVEN** the composer holds a recommendation's brief from **Do this**
- **WHEN** the marketer presses **Send** without editing it
- **THEN** the run request carries the `RECOMMENDATION` `DO_THIS` trigger for
  that recommendation, the transcript shows the brief as the marketer's
  message, and after the run succeeds the card leaves the panel

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

### Requirement: The workspace offers light and dark themes

The workspace SHALL render in a light or a dark theme. With no saved choice
it SHALL follow the operating system's color scheme and track changes to it
live. The TopBar SHALL offer a `Light | Dark | System` menu; a `Light` or
`Dark` choice SHALL override the system and persist across reloads in this
browser, and `System` SHALL clear the override. The page SHALL render in the
resolved theme from its first paint, with no flash of the other theme. Both
themes SHALL meet WCAG AA text contrast. A browser that cannot store the
choice SHALL still follow the system.

#### Scenario: The system dark preference is followed

- **GIVEN** the browser prefers a dark color scheme and no theme was chosen
- **WHEN** the workspace loads at 1440×900
- **THEN** it renders in the dark theme, the theme menu shows `System`
  checked, and an axe accessibility scan reports no violation

#### Scenario: A chosen theme overrides the system and persists

- **GIVEN** the browser prefers a light color scheme
- **WHEN** the marketer picks `Dark` from the theme menu and reloads the page
- **THEN** the workspace renders dark before and after the reload, and
  picking `System` returns it to light

### Requirement: Influencers show their real avatar

The Influencers table SHALL keep exactly two visible columns, Influencer and
Followers. Each row SHALL show the influencer's `avatar_url` as a round image
with an empty `alt` (the linked handle beside it names the person), loaded
lazily; when `avatar_url` is null or the image fails to load, the row SHALL
show the monogram instead. The table SHALL render the influencers in the
order the API returns them.

#### Scenario: Avatars render with a monogram fallback

- **GIVEN** typed fixtures with one influencer that has an `avatar_url`, one
  with a null `avatar_url`, and one whose image fails to load
- **WHEN** the Influencers table renders
- **THEN** the first row shows the image, and the other two show the
  monogram, with no broken-image icon and no axe violation
