# Design

## Context

The three Step 1 pipelines already accept typed source readers and write only through owned repositories. Seed templates are validated by `load_seed_bundle`, while the API contract reserves `POST /activities/simulate` for a later API step. This change supplies the in-process service and operational entry point without adding the route.

## Goals / Non-Goals

**Goals:**

- Keep pipeline selection and scheduling in a small runner layer that reuses the existing async Mongo client and settings.
- Make simulation template selection and fictional-competitor checks explicit, typed, and testable.
- Keep source reads read-only and make every simulation event a separately attributable record.

**Non-Goals:**

- No HTTP/SSE exposure, API schemas, MCP tools, agents, UI, or production deployment automation.

## Decisions

1. **Use a typed runner module plus a thin CLI.** The module accepts database dependencies so dispatch is unit-testable; the script owns argument parsing, JSON output, exit codes, and client cleanup. A shell-only script was rejected because it cannot provide typed error handling or testable selective dispatch.
2. **Schedule with a compose worker loop.** A small service runs the CLI, sleeps a bounded interval, and repeats. This keeps the PoC self-contained without adding a cron image or a new runtime dependency; a host cron can invoke the same CLI later.
3. **Use validated seed templates and repository lookup.** The simulation service receives `SimulationTemplate` values from the seed loader and resolves competitors through `CompetitorsRepository`, rather than trusting template IDs or source documents. Real competitors fail before any write.
4. **Use UUID-backed simulation provenance.** Each event gets `simulation:<uuid>` as `source.ref_id` and an `act_sim_<uuid>` owned ID. This intentionally does not deduplicate repeated demo events; the provenance unique index still prevents accidental replay of one event.
5. **Set `is_mock = true` and `is_simulated = true`.** The activity is generated from mock demo content and must carry both transparency badges; its `SourceSystem.SIMULATED` provenance distinguishes it from seed and source-ingested records.

## Risks / Trade-offs

- [Risk] A scheduler loop can overlap if a pipeline run exceeds its interval → use a single worker process and an interval longer than normal pipeline duration; one invocation completes before the next sleep.
- [Risk] A template can reference a deleted fictional competitor → resolve the competitor at request time and return a validation error without writing.
- [Risk] Simulation content can drift from model rules → construct and validate a `CompetitorActivity` before the repository call and cover every activity type in template tests.

## Migration Plan

No data migration is required. Add the compose worker as an opt-in local service, run the CLI manually for verification, and remove the worker or stop it to roll back; owned simulated records remain identifiable by `source.system = SIMULATED`.
