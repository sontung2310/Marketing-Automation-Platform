# Proposal

Roadmap: 1.5

## Why

Step 1 now has all three normalization pipelines, but there is no reliable operational entry point to run them together or on a schedule. The demo also needs a safe way to create a clearly simulated activity so the live feed can be exercised without attributing fabricated behavior to a real competitor.

## What Changes

- Add a typed pipeline runner and `--only` CLI dispatch for the CompetitorScope, DCT, and Pace pipelines.
- Add a compose scheduler entry that invokes the runner at a bounded interval while preserving read-only source access.
- Add a simulation service backed by the validated seed templates, with fictional-competitor enforcement, explicit simulation provenance, and UTC timestamps.
- Add unit and isolated integration coverage for dispatch, errors, simulation rules, idempotence/provenance, and source immutability.

## Capabilities

### New Capabilities

- `pipeline-runner`: CAP-DATA-01, CAP-DATA-02, and CAP-DATA-03 operational runner behavior for the Step 1 pipelines.
- `simulation-trigger`: CAP-DATA-05 safe creation of simulated competitor activities.

### Modified Capabilities

- None.

## Impact

Adds backend pipeline orchestration and a simulation service, the runner CLI, compose scheduling, tests, and the API/data contract notes needed by the later HTTP endpoint. No API route, MCP tool, agent, frontend, or source-database write changes are included.
