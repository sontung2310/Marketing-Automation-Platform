# Tasks

## 1. Domain contracts and repositories

- [x] 1.1 Add shared enums, prefixed-ID/provenance value objects, and Pydantic models for all owned collections; verify invalid enum, ID, tenant, timestamp, and collection-specific records fail unit tests while valid fixtures round-trip.
- [x] 1.2 Add one typed repository per owned collection with explicit collection names and typed read/upsert methods; verify import-linter and repository unit tests show no Mongo queries outside the allowed layer.
- [x] 1.3 Add centralized idempotent index setup for all repositories, including feed query indexes and the unique `(source.system, source.ref_id)` key; verify repeated setup succeeds and index metadata matches the data contract.

## 2. Seed datasets and validation

- [x] 2.1 Create reviewable JSON seed files under `backend/app/pipelines/seed/` for company context, competitors, activities, trends, influencers, and simulation templates; verify every §5 minimum, mock flag, date window, channel, fictional URL, and provenance rule with unit tests.
- [x] 2.2 Implement the typed seed loader and coverage validator; verify malformed records and missing minimum coverage fail before any Mongo write and valid files produce a deterministic summary.

## 3. Seed execution and integration evidence

- [x] 3.1 Implement async `backend/scripts/seed_db.py` with configured URI/database, `--dry-run`/validation mode, index setup, idempotent provenance upserts, and inserted/updated/skipped totals; verify dry-run leaves counts unchanged.
- [x] 3.2 Add model, seed-rule, repository/index, and two-run integration tests against a disposable or configured Mongo database; verify the second seed run adds no logical records and all §5 counts remain satisfied.
- [ ] 3.3 Update `docs/roadmap.md` and any affected contract documentation with the merged evidence and run `npm run check`; verify the Step 1.1–1.2 checkboxes remain unticked until the PR evidence is complete, then tick them in the same PR.
