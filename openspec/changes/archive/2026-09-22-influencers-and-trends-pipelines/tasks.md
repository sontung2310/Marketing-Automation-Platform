# Tasks

## 1. Source adapters and contracts

- [x] 1.1 Add typed, read-only DCT and Pace source adapters with configured database names, bounded queries, and explicit source-field parsing; verify source unit tests cover malformed documents and no write calls are made
- [x] 1.2 Update the intelligence models' optional collection fields to accept the contract's empty `topics`, `keywords`, and evidence lists while preserving validation for required identity and range fields; verify model unit tests cover empty and invalid values

## 2. Influencer pipeline

- [x] 2.1 Implement DCT platform/channel mapping, handle normalization, engagement-rate calculation, relevance clamping, bounded evidence, and deterministic provenance; verify focused unit tests cover ordering, the 25-candidate cap, unknown-platform skips, and field mapping
- [x] 2.2 Implement the DCT pipeline service using the source adapter and `InfluencersRepository.upsert_by_source`; verify an isolated integration test proves idempotent reruns and source-owned records

## 3. Trend pipeline

- [x] 3.1 Implement Pace source-channel and sentiment registries plus pure 14-day/7-day aggregation with deterministic IDs, momentum direction, keywords, and newest sample posts; verify unit tests cover threshold windows, ties, clamping, and unknown-source skips
- [x] 3.2 Implement the Pace pipeline service with the 50-post seed fallback and live aggregation path; verify isolated integration tests prove fallback performs no live writes and live reruns are idempotent

## 4. Documentation and verification

- [x] 4.1 Update `docs/roadmap.md` and any contract documentation changed by the implementation; verify the roadmap links the PR and the documented defaults match settings
- [x] 4.2 Run the complete quality gate and OpenSpec checks (`npm run check`, `openspec validate --all --strict --no-interactive`, and conflict detection); verify all affected tests and checks pass
