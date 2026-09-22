# Proposal

Roadmap: 1.3

## Why

The owned Intelligence DB currently contains deterministic demo activity, but it does not yet ingest the verified CompetitorScope website-change source. Step 1.3 makes Lyfe Marketing's real changes available to downstream MCP tools and agents while preserving tenant isolation, source immutability, and safe reruns.

## What Changes

- Add an async CompetitorScope source adapter for the verified `competitors_monitoring_test` `changes`, `monitoring_targets`, `competitors`, and `companies` collections.
- Resolve the Marketing Eye source-company allowlist, join changes through monitoring targets to competitors, and skip records with missing or non-matching tenant ownership.
- Normalize supported `change_type` values into typed `CompetitorActivity` records with deterministic titles, website channel, source provenance, timestamps, and preserved simulation flags.
- Skip and log unknown or missing source change types without failing the pipeline.
- Upsert owned competitors and activities by provenance through the existing repositories, with unit and Mongo-backed integration coverage for idempotency and source-shape edge cases.

## Capabilities

### New Capabilities

- `competitor-activity-pipeline`: Normalize verified CompetitorScope changes into tenant-scoped owned competitor activities (CAP-DATA-01).

### Modified Capabilities

- None.

## Impact

- Affected backend layers: `pipelines/sources/`, the CompetitorScope pipeline service, existing intelligence repositories/models, and pipeline tests.
- No API, MCP, agent, frontend, or source-database write changes.
- Uses the existing async PyMongo dependency and `SourceSystem.COMPETITORSCOPE`; no new runtime dependency is expected.
