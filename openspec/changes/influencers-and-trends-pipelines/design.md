# Design

## Context

The owned `Influencer` and `Trend` models and provenance repositories are available. The frozen source mapping identifies DCT `influencer_discovery.influencer_candidates` and Pace `pace_database.ai_posts`; the current Pace collection has zero posts in the 14-day window and remains below the 50-post live aggregation threshold.

## Goals / Non-Goals

**Goals:**

- Keep DCT and Pace reads in dedicated typed source adapters and owned writes in repositories.
- Use separate registries for DCT platforms, Pace sources, Pace sentiment labels, and trend directions.
- Make DCT selection and Pace aggregation deterministic, observable, idempotent, and safe to rerun.
- Preserve the seed fallback as the authoritative trend set while live Pace volume is insufficient.

**Non-Goals:**

- Topic classification for DCT candidates, API/MCP exposure, cron/CLI orchestration, simulation, agents, or UI work.
- Writes to DCT, Pace, or any source collection.

## Decisions

1. **Reuse the existing Mongo URI with source database settings.** Add `DCT_DATABASE` and `PACE_DATABASE` settings with the verified defaults, using the existing async client. This keeps source selection configurable without introducing extra clients.

2. **Normalize DCT in Python after a bounded source query.** Read the verified candidate filter and sort, cap at 25, then calculate engagement and evidence from typed recent posts. This makes unknown platform and malformed nested fields explicit skips rather than relying on aggregation expressions to guess types.

3. **Use one run-time Pace window and pure aggregation helpers.** Capture `window_end_date` once, parse qualifying posts into typed records, group by topic/channel, and compute counts, momentum, sentiment, keywords, and samples in Python. An all-Mongo aggregation was rejected because the source has heterogeneous nested fields and the fallback/diagnostic rules are easier to test as typed functions.

4. **Preserve seed fallback by not deleting or rewriting trends.** When the live count is below 50, return a fallback summary and do not call the trends repository. This keeps the committed seed set intact and makes the eventual live switch automatic when volume crosses the threshold.

5. **Use deterministic aggregate provenance.** For live trends, hash the UTF-8 topic and compose the documented date/channel key; upsert with the existing provenance-safe repository and stable `inf_`/`trd_` IDs.

## Risks / Trade-offs

- [Risk] DCT nested metrics or Pace sentiment values may be malformed. → Treat them as non-qualifying metrics, log source IDs, and use the documented zero fallback rather than failing the run.
- [Risk] A live Pace run can coexist with seeded trends. → Only write live trends when the threshold is met; the later run can explicitly replace or supersede seed records in its own follow-up contract if needed.
- [Risk] Source collections may be large. → Apply the DCT limit and Pace date filter before normalization, and keep sample/evidence arrays bounded.

## Migration Plan

No source migration is required. The current deployment continues using seeded trends; once live Pace volume meets the threshold, the next pipeline run writes dated `PACE` aggregates through idempotent upserts. Rerunning the pipeline is the rollback-safe operation.
