# Delta: workspace-ui

**Why:** the live site showed that a **Do this** brief sent as plain chat loses
which recommendation it came from, so the router asked a question instead of
running Execution (specs §6: "Do this" sends the recommendation to Execution).

## MODIFIED Requirements

### Requirement: Strategy output stays in its own panel and reaches Execution by an explicit action

Strategy recommendations SHALL never enter the Execution transcript. Each
recommendation SHALL render as a compact row grouped under the run that
produced it, showing its ordinal, priority, the decision at body weight 600,
its status and its `next_action` in plain words. Opening a row SHALL open a
440px sheet with what to do, why, evidence chips and **Do this**. **Do this**
SHALL write the recommendation's brief into the Execution composer and SHALL
NOT start a run. When the marketer sends that brief unedited, the run SHALL
start from the `RECOMMENDATION` `DO_THIS` trigger, so Execution receives that
recommendation; an edited brief SHALL be sent as a chat message. An evidence
chip SHALL show a short title, keep its raw evidence ID in its tooltip, and on
activation scroll to and flash-highlight its target item.

#### Scenario: Do this prefills the composer without sending

- **GIVEN** Strategy recommendations in the fixture
- **WHEN** the marketer opens a recommendation and clicks **Do this**
- **THEN** the 440px sheet showed the decision, rationale and evidence, the
  recommendation's request is in the Execution composer, and no run was
  created

#### Scenario: Sending the unedited brief runs that recommendation

- **GIVEN** the composer holds a recommendation's brief from **Do this**
- **WHEN** the marketer presses **Send** without editing it
- **THEN** the run request carries the `RECOMMENDATION` `DO_THIS` trigger for
  that recommendation, and the transcript shows the brief as the marketer's
  message

#### Scenario: An evidence chip navigates to its source

- **GIVEN** an open recommendation sheet citing a feed item
- **WHEN** the marketer activates that evidence chip
- **THEN** the feed scrolls to the cited item and flash-highlights it
