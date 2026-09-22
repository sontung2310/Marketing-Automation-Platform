# Tasks

## 1. Source adapter and typed normalization

- [x] 1.1 Add the configurable CompetitorScope source database setting and typed read-only adapter for the `changes`, `monitoring_targets`, `competitors`, and `companies` collections; verify the adapter resolves exactly one Marketing Eye source-company ObjectId and never calls an owned repository.
- [x] 1.2 Implement the registry-based `change_type` mapping, deterministic title helper, source-field fallbacks, and typed conversion to owned competitor/activity models; verify unit tests cover every supported type, missing fields, title truncation, and unknown-type skips.
- [x] 1.3 Implement tenant filtering and source-join handling for missing targets, missing competitor ownership, and other-tenant competitors; verify unit tests assert each excluded record is skipped with its source ID logged.

## 2. Owned writes and pipeline service

- [x] 2.1 Upsert source competitors by `COMPETITORSCOPE` provenance and reuse their stable `cpt_` IDs; verify a differing-ID rerun updates one competitor without creating a duplicate.
- [x] 2.2 Implement the async competitor activity pipeline with typed inserted/updated/skipped/total summaries and warning logs; verify `npm run typecheck` and targeted unit tests pass.

## 3. Integration evidence and repository bookkeeping

- [x] 3.1 Add `backend/tests/integration/test_competitor_pipeline.py` using a seeded copy of the verified source document shape; verify eligible Lyfe changes normalize once, reruns insert zero new records, and source collections remain unchanged.
- [x] 3.2 Run `npm run check` and the scoped integration suite against MongoDB; verify all checks are green.
- [x] 3.3 Update `docs/roadmap.md` with the merged PR evidence and update `docs/data-contract.md` only if implementation reveals a mapping correction; verify OpenSpec validation and the roadmap conflict check pass.
