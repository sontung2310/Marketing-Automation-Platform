# Proposal

Roadmap: 1.4

## Why

The owned Intelligence DB currently has only seeded influencer and trend records. Step 1.4 adds the verified DCT candidates and the Pace trend source with the documented volume guard, so the platform uses real ranked influencer evidence while safely falling back to the seed until Pace has enough recent posts.

## What Changes

- Add a typed, read-only DCT source adapter and normalize the bounded Marketing Eye candidate set into owned influencers.
- Add typed DCT platform mapping, score/engagement/evidence calculations, unknown-platform skips, and deterministic provenance upserts.
- Add a typed Pace source adapter and trend aggregation with source/channel/sentiment registries, dated aggregate provenance, momentum calculations, and sample posts.
- Keep the seeded trends active when Pace has fewer than 50 posts in the 14-day window, reporting the fallback without fabricating live trends.
- Add unit and Mongo-backed integration coverage for filtering, registries, fallback, aggregation, idempotency, and source immutability.

## Capabilities

### New Capabilities

- `influencer-pipeline`: Normalize bounded DCT influencer candidates into tenant-scoped owned influencers (CAP-DATA-02).
- `trend-pipeline`: Aggregate Pace `ai_posts` into dated trends with a seed fallback when live volume is insufficient (CAP-DATA-03).

### Modified Capabilities

- None.

## Impact

- Affected backend layers: `pipelines/sources/`, pipeline services, existing intelligence repositories/models, configuration, and tests.
- No API, MCP, agent, frontend, simulation, cron, or source-database write changes.
- Reuses the existing async PyMongo dependency and typed domain contracts; no new runtime dependency is expected.
