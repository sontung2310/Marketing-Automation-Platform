# Spec Delta

## MODIFIED Requirements

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
