# run-orchestration Specification

## Purpose
Starts agent runs from UI triggers or chat messages, routes UI triggers
deterministically, and persists sessions, runs and their event logs so later
steps can stream, replay and reference them.

## Requirements

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

### Requirement: Runs, sessions and events are persisted

Each run SHALL belong to a session (created when absent) and SHALL persist its
agent, intent, trigger, route, status, ordered events with increasing `seq`,
tool calls, skills loaded, structured output, token usage (every run,
including a failed, timed-out or cancelled one: usage accumulates as each
model call completes and is recorded whatever the run's outcome), error and
timestamps. The event log SHALL contain `run.started`, one or more
`agent.step`/`agent.tool` events, then `output.final` and `run.completed`, or
`run.failed` on error. The session SHALL record its latest successful run, so
a failure, refusal or clarification never replaces the answer follow-ups build
on.

#### Scenario: A completed run has an ordered event log

- **GIVEN** a Strategy run that completes
- **WHEN** the run document is read
- **THEN** its events start with `run.started`, end with `run.completed`,
  contain `output.final`, and their `seq` values strictly increase

#### Scenario: A cancelled run is finalised

- **GIVEN** a run in progress
- **WHEN** it is cancelled (client disconnect or timeout)
- **THEN** it is saved as `FAILED` with code `CANCELLED`, a `run.failed`
  event and `finished_at`, and it is not left `RUNNING`

#### Scenario: A failing run records the failure

- **GIVEN** the model or MCP call fails during a run
- **WHEN** the run ends
- **THEN** its status is `FAILED`, a `run.failed` event carries a code and
  message (`UPSTREAM_UNAVAILABLE` when OpenAI or the MCP is unreachable, a
  fixed `INTERNAL` message for unexpected errors), and no partial
  recommendations are persisted

#### Scenario: Usage is recorded when a run fails after spending tokens

- **GIVEN** a run whose first model call succeeds and whose second call (a
  repair) exceeds the run's wall-clock limit
- **WHEN** the run is stopped and saved as `FAILED`
- **THEN** the persisted run's `usage` SHALL be non-empty and SHALL include
  the first call's tokens

#### Scenario: A clean failure before any model call logs empty usage

- **GIVEN** a run whose trigger fails to resolve before any model call is
  made
- **WHEN** the run fails
- **THEN** the persisted run's `usage` SHALL be present and empty, not
  absent

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
