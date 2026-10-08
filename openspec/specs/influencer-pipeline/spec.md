# influencer-pipeline Specification

## Purpose
Normalizes the bounded, eligible Marketing Eye candidate set from DCT into typed owned influencers with transparent ranking and evidence rules.

## Requirements

### Requirement: DCT candidates are filtered and normalized safely

The system SHALL read only eligible DCT candidates for `company_id = marketingeye.com.au` with numeric `evaluation.latest_final_score`, order them by score descending, then `profile.followers` descending (a missing follower count sorts last), then source `_id` ascending, and ingest at most 10 records into owned influencers.

#### Scenario: Eligible candidates are ranked and bounded

- **GIVEN** DCT contains eligible and ineligible candidates for multiple companies
- **WHEN** the influencer pipeline runs
- **THEN** only the eligible Marketing Eye candidates are considered, the highest scores are selected in deterministic order with ties broken by more followers first, and no more than 10 owned influencers are written

#### Scenario: Unknown platform is skipped

- **GIVEN** a selected candidate has a platform not present in the documented DCT platform registry
- **WHEN** the pipeline normalizes candidates
- **THEN** it skips and logs that source ID without guessing a channel, and continues processing other candidates

#### Scenario: Candidate fields follow the source contract

- **GIVEN** a selected candidate has profile, account, follower, avatar, score, and recent-post fields
- **WHEN** it is normalized
- **THEN** the owned influencer has the mapped channel, the handle and profile URL from `account`, the follower count and `avatar_url` from `profile` (null when absent), bounded evidence from recent posts, mean engagement rate, clamped relevance score, empty topics, and `audience_region = UNKNOWN` with `source.system = DCT`

### Requirement: DCT writes are idempotent and source-safe

The system SHALL upsert DCT-derived influencers by source provenance, delete owned DCT influencers whose source is no longer in the selected top 10, report inserted/updated/deleted/skipped counts, and never modify DCT collections.

#### Scenario: Rerun converges

- **GIVEN** the same DCT candidate set is processed twice
- **WHEN** the second run completes
- **THEN** it inserts no duplicate provenance records, preserves stable owned influencer IDs, and the collection holds exactly the 10 selected DCT records

#### Scenario: A candidate that drops out is removed

- **GIVEN** an owned DCT influencer whose candidate is no longer in the top 10
- **WHEN** the pipeline runs
- **THEN** that owned influencer is deleted and the deletion is counted
