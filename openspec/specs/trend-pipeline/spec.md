# trend-pipeline Specification

## Purpose
Builds tenant-scoped trends from recent Pace posts when volume is sufficient and keeps the documented seeded trends as the safe fallback while the live source is sparse.

## Requirements

### Requirement: Pace volume determines live aggregation or seed fallback

The system SHALL inspect Pace `ai_posts` in the 14-day window and use the seeded trend set when fewer than 50 posts qualify, without fabricating live aggregates; once the threshold is met it SHALL aggregate by enriched topic and mapped source channel.

#### Scenario: Current sparse Pace source uses seed fallback

- **GIVEN** Pace has fewer than 50 posts in the 14-day window
- **WHEN** the trend pipeline runs
- **THEN** it leaves the owned trends on the seeded `is_mock = true` set, reports the fallback, and performs no live trend upserts

#### Scenario: Sufficient Pace source aggregates deterministically

- **GIVEN** Pace has at least 50 qualifying posts with recognized sources and topics
- **WHEN** the trend pipeline runs
- **THEN** it groups by topic and mapped channel, computes seven-day mention count and momentum against the prior seven days, maps direction and sentiment, and retains at most three newest sample posts per group

#### Scenario: Unknown Pace source is skipped

- **GIVEN** a Pace post has an unrecognized `source`
- **WHEN** the aggregation runs
- **THEN** it skips and logs that source ID without guessing a channel or including the post

### Requirement: Pace aggregates are dated and idempotent

The system SHALL capture one UTC window-end date per run, derive the documented hashed aggregate provenance key, upsert trends by that key, and preserve source read-only behavior.

#### Scenario: Same window rerun updates one aggregate

- **GIVEN** the same Pace window and topic/channel group is processed twice
- **WHEN** the second run completes
- **THEN** exactly one owned trend exists for that provenance key and its aggregate is updated rather than duplicated
