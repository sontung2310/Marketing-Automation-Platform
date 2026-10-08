## MODIFIED Requirements

### Requirement: Strategy output stays in its own panel and reaches Execution by an explicit action

Strategy recommendations SHALL never enter the Execution transcript. The
Strategy panel header SHALL carry a **Generate strategy** button that starts
a run with the `COMPANY` `GENERATE_STRATEGY` trigger; while a Strategy run is
in flight the button SHALL be disabled and the header SHALL show a labelled
working status. The panel SHALL show only the company's `OPEN`
recommendations and SHALL refresh when a run completes. Each
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

## ADDED Requirements

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
