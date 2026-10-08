## MODIFIED Requirements

### Requirement: UI triggers route deterministically without an LLM

The system SHALL map each UI trigger `{kind, action}` to an agent and intent
using the table in agents-spec §5.1, without calling a model. A trigger whose
`ref_id` does not resolve to a record of the current company SHALL be
rejected before any run starts. `COMPANY` + `GENERATE_STRATEGY` (whose
`ref_id` is the company's ID), `FEED_ACTION` + `RESPONSE_PLAN` and `TREND` +
`USE_TREND` SHALL all route to Strategy with intent `STRATEGY_SYNTHESIS`;
the latter two SHALL pass their resolved record as the run's focus. A chat
message SHALL be routed by the classifier router (chat-router spec).

#### Scenario: A feed button starts a Strategy run

- **GIVEN** the seeded database and a `PRICE_CHANGE` activity
- **WHEN** a run starts with trigger `FEED_ACTION` + `RESPONSE_PLAN` for it
- **THEN** the run is created for agent `STRATEGY` with intent
  `STRATEGY_SYNTHESIS`, route method `DETERMINISTIC`, and the resolved
  activity in its trigger context as the focus

#### Scenario: Generate strategy starts an unfocused synthesis

- **GIVEN** the seeded database
- **WHEN** a run starts with trigger `COMPANY` + `GENERATE_STRATEGY` and the
  company's ID
- **THEN** the run is created for agent `STRATEGY` with intent
  `STRATEGY_SYNTHESIS`, route method `DETERMINISTIC`, and no focus record

#### Scenario: An unknown reference is rejected

- **GIVEN** a trigger whose `ref_id` matches no record for the company
- **WHEN** a run is requested
- **THEN** the request fails with a not-found error and no run is persisted

## ADDED Requirements

### Requirement: A recommendation acted on is marked done

When an Execution run whose trigger context is a recommendation (the
`RECOMMENDATION` `DO_THIS` trigger, or a resolved `#N` reference) completes
successfully with a deliverable, the system SHALL set that recommendation's
status to `DONE`. A failed, refused or clarifying run SHALL leave it
unchanged.

#### Scenario: Do this completes the recommendation

- **GIVEN** an `OPEN` recommendation
- **WHEN** an Execution run started from its `DO_THIS` trigger succeeds with
  a deliverable
- **THEN** the recommendation is `DONE` and `GET /api/recommendations` no
  longer returns it

#### Scenario: A failed run keeps the recommendation open

- **GIVEN** an `OPEN` recommendation
- **WHEN** an Execution run started from it fails
- **THEN** the recommendation stays `OPEN`
