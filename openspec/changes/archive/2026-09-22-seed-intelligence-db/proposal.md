# Proposal

## Why

Step 1 currently has no owned data layer: the normalized collections, typed boundaries, indexes, and demo data that every pipeline and MCP tool depends on are still absent. Building this foundation now makes the verified source contract executable, gives the PoC deterministic coverage, and prevents later agent work from inventing ad hoc Mongo queries or fixtures.

## What Changes

- Add Pydantic v2 models for every owned collection and the documented enums, IDs, provenance, tenant, and timestamp fields.
- Add one typed repository per owned collection under `backend/app/intelligence/repositories/`, with idempotent index creation and a unique provenance key.
- Add realistic JSON seed datasets and an async `backend/scripts/seed_db.py` CLI that validates/dry-runs, upserts safely, and reports counts.
- Add model, seed-rule, index, and two-run idempotency tests against the configured or disposable database.
- Keep CompetitorScope, DCT, and Pace source collections read-only; all owned writes target `marketing_automation`.

## Capabilities

### New Capabilities

- `intelligence-db-foundation`: Typed owned-collection models, repositories, indexes, and an idempotent seed dataset/CLI for roadmap 1.1–1.2, implementing CAP-DATA-04.

### Modified Capabilities

None.

## Impact

- Backend domain models, Mongo repositories, startup/index wiring, seed files, and the seed CLI.
- Backend unit/integration test coverage and the roadmap evidence for Step 1.
- No API or frontend behavior changes, no new runtime dependency, and no writes to source databases.
