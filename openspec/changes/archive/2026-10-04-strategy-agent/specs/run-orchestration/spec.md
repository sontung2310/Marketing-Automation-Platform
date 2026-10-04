# Spec Delta

## Purpose

Starts agent runs from UI triggers or chat messages, routes UI triggers
deterministically, and persists sessions, runs and their event logs so later
steps can stream, replay and reference them.

## ADDED Requirements

### Requirement: UI triggers route deterministically without an LLM

The system SHALL map each UI trigger `{kind, action}` to an agent and intent
using the table in agents-spec §5.1, without calling a model. A trigger whose
`ref_id` does not resolve to a record of the current company SHALL be
rejected before any run starts. A chat message SHALL run only with an explicit
agent selection until the Step 6 classifier exists.

#### Scenario: A feed button starts a Strategy run

- **GIVEN** the seeded database and a `PRICE_CHANGE` activity
- **WHEN** a run starts with trigger `FEED_ACTION` + `RESPONSE_PLAN` for it
- **THEN** the run is created for agent `STRATEGY` with intent
  `RESPONSE_PLAN`, route method `DETERMINISTIC`, and the resolved activity in
  its trigger context

#### Scenario: An unknown reference is rejected

- **GIVEN** a trigger whose `ref_id` matches no record for the company
- **WHEN** a run is requested
- **THEN** the request fails with a not-found error and no run is persisted

### Requirement: Runs, sessions and events are persisted

Each run SHALL belong to a session (created when absent) and SHALL persist its
agent, intent, trigger, route, status, ordered events with increasing `seq`,
tool calls, skills loaded, structured output, token usage (successful runs;
failed-run usage is roadmap 8.3), error and timestamps. The event log SHALL contain `run.started`, one or more
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
