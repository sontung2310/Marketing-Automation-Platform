# Design

## Context

The owned models and repositories are available after Step 1.1–1.2. The source mapping in `docs/data-contract.md` fixes a read-only join from `competitors_monitoring_test.changes` through `monitoring_targets` and `competitors` to the single source company named `Marketing Eye`; source documents use Mongo ObjectIds while owned records use prefixed string IDs.

## Goals / Non-Goals

**Goals:**

- Keep source reads in a dedicated pipeline source adapter and keep owned writes in intelligence repositories.
- Normalize every currently supported CompetitorScope change type, with registry-based mapping and deterministic title construction.
- Preserve tenant isolation, source provenance, stable competitor identity, idempotent activity upserts, and observable run counts.
- Exercise the real source shape in integration tests without mutating the source database.

**Non-Goals:**

- DCT, Pace, simulation, cron scheduling, API/MCP exposure, or frontend work.
- New crawler behavior or writes to CompetitorScope collections.
- Copying source companies into the owned company collection.

## Decisions

1. **Use one source adapter for the full join.** `pipelines/sources/competitorscope.py` owns the async Mongo reads and returns typed source records. It resolves the exact `{name: "Marketing Eye"}` source-company ObjectId once, then filters competitors by that allowlist before reading changes. This keeps the tenant rule explicit and prevents an accidental owned-database lookup. An alternative of joining in repositories was rejected because repositories may only query owned collections.

2. **Keep the source database configurable with the verified default.** Add a `COMPETITORSCOPE_DATABASE` setting defaulting to `competitors_monitoring_test`, while reusing the existing Mongo URI/client. This preserves the frozen mapping and makes a future cluster/database move an environment change rather than a code change. A second client or hard-coded database name was rejected.

3. **Normalize through registries and typed conversion.** A registry maps source `change_type` strings to `ActivityType`; unsupported or missing values return a structured skip and a warning log. A separate title helper implements the documented narrative/URL/fallback and Unicode-code-point cap. This avoids branching that must be edited for every future enum value and avoids parsing free prose.

4. **Upsert competitor before activity.** For each eligible source competitor, upsert a `Competitor` by `COMPETITORSCOPE` provenance and resolve the stored `cpt_` ID. Then build and upsert the `CompetitorActivity` with the same source provenance. This guarantees activity references remain stable when source ObjectIds are encountered again.

5. **Return a pipeline summary.** The pipeline returns typed per-stage counts (`inserted`, `updated`, `skipped`, `total`) and logs skipped source IDs with reasons. The CLI is intentionally deferred to Step 1.5; the service is directly callable by tests and the later orchestrator.

## Risks / Trade-offs

- [Risk] A source record may refer to a missing monitoring target, competitor, or URL. → Skip unresolved joins with a reason and continue; only eligible, fully resolvable records become activities.
- [Risk] Source fields may contain Mongo types or nulls not present in the demo sample. → Parse at the adapter boundary with typed source models and explicit nullable fallbacks; reject malformed records as skipped input rather than leaking raw documents inward.
- [Risk] The source tenant company may be absent or duplicated. → Require exactly one `Marketing Eye` source-company row and fail the run before any owned writes if that invariant is violated.

## Migration Plan

No data migration is required. Deploying the pipeline adds only owned competitors and activities through idempotent provenance upserts; rerunning it is the rollback-safe operation. The source database is never modified.
