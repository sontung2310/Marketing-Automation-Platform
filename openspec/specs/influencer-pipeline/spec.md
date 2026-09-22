# influencer-pipeline Specification

## Purpose
Normalizes the bounded, eligible Marketing Eye candidate set from DCT into typed owned influencers with transparent ranking and evidence rules.

## Requirements

### Requirement: DCT candidates are filtered and normalized safely

The system SHALL read only eligible DCT candidates for `company_id = marketingeye.com.au` with numeric `evaluation.latest_final_score`, order them by score descending then source `_id` ascending, and ingest at most 25 records into owned influencers.

#### Scenario: Eligible candidates are ranked and bounded

- **GIVEN** DCT contains eligible and ineligible candidates for multiple companies
- **WHEN** the influencer pipeline runs
- **THEN** only the eligible Marketing Eye candidates are considered, the highest scores are selected in deterministic order, and no more than 25 owned influencers are written

#### Scenario: Unknown platform is skipped

- **GIVEN** a selected candidate has a platform not present in the documented DCT platform registry
- **WHEN** the pipeline normalizes candidates
- **THEN** it skips and logs that source ID without guessing a channel, and continues processing other candidates

#### Scenario: Candidate fields follow the source contract

- **GIVEN** a selected candidate has profile, account, follower, score, and recent-post fields
- **WHEN** it is normalized
- **THEN** the owned influencer has the mapped channel, bounded evidence from recent posts, mean engagement rate, clamped relevance score, empty topics, and `audience_region = UNKNOWN` with `source.system = DCT`

### Requirement: DCT writes are idempotent and source-safe

The system SHALL upsert DCT-derived influencers by source provenance, report inserted/updated/skipped counts, and never modify DCT collections.

#### Scenario: Rerun converges

- **GIVEN** the same DCT candidate set is processed twice
- **WHEN** the second run completes
- **THEN** it inserts no duplicate provenance records and preserves stable owned influencer IDs
