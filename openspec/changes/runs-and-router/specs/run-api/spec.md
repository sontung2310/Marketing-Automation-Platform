# Spec Delta

## Purpose
Agent runs over HTTP: starting a run, streaming its events live with replay, reading a run or a whole session back, and capping how many runs the public demo can start per day.

## ADDED Requirements

### Requirement: Starting a run

`POST /api/runs` SHALL accept exactly one of `message` or `trigger`, plus an optional `session_id` and `agent_hint`. When an agent will run, it SHALL return `202 {run_id, session_id, agent, intent, route}` without waiting for the agent. When the router answers without a run, it SHALL return `200` with `run_id: null` and `response: {status, message, clarification_options}`. Both or neither of `message` and `trigger` return `422`, and an unknown trigger `ref_id` returns `404`.

#### Scenario: Feed action returns fast and streams in order (6-C)
- **GIVEN** a seeded activity
- **WHEN** `POST /api/runs` is called with a `FEED_ACTION` trigger
- **THEN** `202` returns within 500 ms, and the run's event stream emits `run.started`, at least one `agent.step`, then `output.final` and `run.completed`, in that order, with increasing `seq`

#### Scenario: Both message and trigger
- **WHEN** a request carries both `message` and `trigger`
- **THEN** `422` returns the `VALIDATION_ERROR` envelope and no run is created

### Requirement: Live run events with replay

`GET /api/runs/{run_id}/events` SHALL stream the run's events as they are emitted, each with `id` equal to its `seq`. A reconnect with `Last-Event-ID: n` SHALL replay events after `n` with no duplicates. The stream SHALL end after `run.completed` or `run.failed`, and MAY close earlier on a bounded schedule (serverless); clients reconnect with `Last-Event-ID`. An unknown run returns `404`.

#### Scenario: Reconnect replays the rest (6-D)
- **GIVEN** a client that read events up to `seq` 3 and disconnected
- **WHEN** it reconnects with `Last-Event-ID: 3`
- **THEN** events 4..n arrive once each, in order

#### Scenario: Interrupted run does not hang
- **GIVEN** a run still `RUNNING` past the run wall-clock limit (its worker died)
- **WHEN** its events or the run are read
- **THEN** it is reported `FAILED` with "The run was interrupted", and the stream ends

### Requirement: Reading runs and sessions

`GET /api/runs/{run_id}` SHALL return the persisted run. `GET /api/sessions/{session_id}` SHALL return `{id, runs}`, oldest first. Each finished run's `output` SHALL carry the same payload as its `output.final` event, including the persisted `recommendation_ids`, `deliverable_id` and `proposed_action_ids` and the stored proposed actions, so a restored workspace can still approve or discard.

#### Scenario: Restored deliverable can be approved
- **GIVEN** a session whose Execution run proposed an action
- **WHEN** the workspace restores the session after a reload
- **THEN** the run's `output` includes the action's ID, and `POST /api/actions/{id}/approve` succeeds

### Requirement: Daily run cap

The API SHALL refuse to start an agent run when `MAX_RUNS_PER_DAY` runs have already started for the company that UTC day, returning `429` with code `RATE_LIMITED` and the message "The demo's daily run limit is reached. Try again tomorrow." Router answers that start no run do not count, and neither do reads.

#### Scenario: Cap reached
- **GIVEN** `MAX_RUNS_PER_DAY=2` and two runs started today
- **WHEN** a third run is requested
- **THEN** `429 RATE_LIMITED` returns and no run is created, while `GET` endpoints keep working
