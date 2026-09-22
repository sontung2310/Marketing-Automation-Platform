# Design

## Context

The repository currently has the async shared Mongo client and health probe, but no owned collection models, repositories, seed files, or seed CLI. The verified contract defines one owned database (`MONGODB_DATABASE`, default `marketing_automation`), five intelligence collections, five app-state collections, stable prefixed IDs, and provenance/index rules. Source databases remain read-only. See `proposal.md` and `specs/intelligence-db-foundation/spec.md` for the behavior contract.

## Goals / Non-Goals

**Goals:**

- Keep all owned Mongo access behind typed repositories and a single index-setup path.
- Validate seed JSON before any write and make writes deterministic and idempotent.
- Make the §5 minimums executable as tests rather than tribal knowledge.
- Preserve tenant scoping and provenance so later pipelines can upsert into the same collections.

**Non-Goals:**

- Reading or writing CompetitorScope, DCT, or Pace sources; those adapters belong to later Step 1 changes.
- Adding API routes, MCP tools, agent behavior, or frontend screens.
- Introducing a second database, ORM, migration framework, or runtime dependency.

## Decisions

1. **One model module per domain group, one repository per collection.** Keep enums and shared value objects in `app/intelligence/models`, collection models alongside them, and repositories in `app/intelligence/repositories`. This follows the existing layering rule and makes import-linter checks able to prove that only repositories touch Mongo. A generic repository abstraction was rejected because collection-specific filters and validation are clearer in explicit methods.

2. **JSON seed files plus a typed loader.** JSON keeps seed data reviewable and editable without executable code. The loader parses each file into the same boundary models used by repositories, then applies centralized §5 validation. Python literals were rejected because they hide data diffs and make validation less reusable.

3. **Deterministic provenance upserts.** Provenance-bearing records use `(source.system, source.ref_id)` as the logical key and stable prefixed `_id` values from the seed files. `bulk_write` with `UpdateOne(..., upsert=True)` gives repeatable runs and useful inserted/modified counts; the unique index protects against accidental duplicates.

4. **Explicit startup index hook.** A single async `ensure_indexes` entry point calls each repository’s index definitions and is invoked by the seed CLI and application startup wiring. `create_indexes` is idempotent, so no migration state table is needed for the PoC.

5. **Dry-run before writes.** The CLI loads, validates, and summarizes every dataset first. `--dry-run` stops before opening write operations; default mode ensures indexes and upserts only after validation passes. Partial writes from invalid seed data are therefore avoided.

## Risks / Trade-offs

- **[Risk]** Seed files can drift from the contract as enums or minimums evolve → **Mitigation:** model validation and §5 coverage tests fail `npm run check` when a required field, type, or minimum changes.
- **[Risk]** A stable seed `_id` can collide with a future pipeline record → **Mitigation:** seed provenance uses `MOCK_SEED` and explicit `seed:` reference IDs; repository upsert keys remain namespaced by source system.
- **[Risk]** The configured remote cluster may be unavailable in CI → **Mitigation:** unit tests use an in-memory/fake repository boundary; the integration idempotency test is marked for a configured Mongo service and compose can provide disposable Mongo for local runs.
- **[Risk]** A large JSON file is awkward to review → **Mitigation:** keep one file per collection/template family, use concise records, and report deterministic counts in the CLI.

## Migration Plan

No migration is required. On first startup or seed execution, the owned database is created lazily and indexes are ensured. Rollback is reverting the PR; source collections are untouched and seeded owned records can be removed from the disposable PoC database without affecting source data.
