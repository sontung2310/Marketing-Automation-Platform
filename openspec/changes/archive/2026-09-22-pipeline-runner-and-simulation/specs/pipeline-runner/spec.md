# Spec Delta

## Purpose

Provides a repeatable operational entry point for running the three Step 1 intelligence pipelines together or individually, with bounded scheduling and structured outcomes.

## ADDED Requirements

### Requirement: Pipeline runner dispatches selected pipelines

The system SHALL run CompetitorScope, DCT, and Pace normalization pipelines in a deterministic order by default, and SHALL run only the named pipeline when `--only` selects one of `competitor_activity`, `influencers`, or `trends`.

#### Scenario: Default run executes every pipeline

- **GIVEN** the configured source databases and owned database are reachable
- **WHEN** the pipeline runner is invoked without `--only`
- **THEN** it runs competitor activities, influencers, and trends in that order and emits structured counts for each

#### Scenario: Selective run executes one pipeline

- **GIVEN** the configured databases are reachable
- **WHEN** the runner is invoked with `--only influencers`
- **THEN** it runs only the DCT influencer pipeline and emits no competitor or trend result

#### Scenario: Invalid selection fails safely

- **GIVEN** a runner invocation names an unsupported pipeline
- **WHEN** argument validation runs
- **THEN** the process exits non-zero with a machine-readable validation error and performs no pipeline writes

### Requirement: Scheduled runner preserves source read-only behavior

The system SHALL expose a bounded compose scheduler entry that invokes the same runner CLI, uses the configured source database settings, and never writes to CompetitorScope, DCT, or Pace collections.

#### Scenario: Scheduler invokes the runner

- **GIVEN** the local compose stack is started with a valid `.env`
- **WHEN** one scheduler interval elapses
- **THEN** the runner is invoked once and its structured result is logged without changing the source databases
