# competitor-activity-pipeline Specification

## Purpose

Normalizes verified CompetitorScope website changes into tenant-scoped owned activities so the feed and downstream intelligence tools can consume real evidence safely and repeatably.

## Requirements

### Requirement: CompetitorScope changes are tenant-safe and read-only

The system SHALL read CompetitorScope changes through the verified source join, allow only competitors whose source `company_id` belongs to the single source company named `Marketing Eye`, and SHALL never write to the source database.

#### Scenario: Eligible Marketing Eye change is ingested

- **GIVEN** a source change joins through `monitoring_targets` to a competitor whose `company_id` is the Marketing Eye source-company ObjectId
- **WHEN** the CompetitorScope pipeline runs
- **THEN** it produces one owned activity with `company_id = cmp_marketing_eye`, the joined competitor identity, and `source.system = COMPETITORSCOPE`

#### Scenario: Unscoped or other-tenant change is excluded

- **GIVEN** a source change joins to a competitor with a missing `company_id` or a `company_id` outside the Marketing Eye allowlist
- **WHEN** the pipeline runs
- **THEN** it skips the change and does not create an owned activity or competitor record for it

#### Scenario: Source collections remain unchanged

- **GIVEN** the source collections contain changes, monitoring targets, competitors, and companies
- **WHEN** the pipeline runs
- **THEN** it performs reads only against those collections and leaves their documents unchanged

### Requirement: Supported changes are normalized with deterministic contracts

The system SHALL map supported CompetitorScope `change_type` values to the documented `ActivityType` enum, set `channel = WEBSITE`, preserve source summaries and simulation flags, use the detected timestamp for both occurrence and detection, and generate a non-empty title capped at 120 Unicode code points using the documented fallback order.

#### Scenario: Supported change has the expected activity fields

- **GIVEN** an eligible source change with a supported `change_type`, URL, summary, narrative summary, and detected timestamp
- **WHEN** the pipeline normalizes it
- **THEN** the owned activity has the mapped `activity_type`, `WEBSITE` channel, source reference from the source `_id`, preserved summary fields, `occurred_at = detected_at`, and the source `is_simulated` value with missing treated as false

#### Scenario: Title fallback is deterministic and bounded

- **GIVEN** an eligible source change with an empty narrative summary, an optional detected URL, and an optional target URL
- **WHEN** the pipeline builds its title
- **THEN** it selects the first non-empty candidate in the documented order and truncates any title longer than 120 Unicode code points to 117 code points plus `...`

#### Scenario: Unknown change type is skipped safely

- **GIVEN** an eligible source change with an unknown or missing `change_type`
- **WHEN** the pipeline runs
- **THEN** it skips the record, logs its source `_id`, and continues processing other changes successfully

### Requirement: Pipeline writes are idempotent and observable

The system SHALL upsert owned competitors and activities by provenance, reusing the stored prefixed competitor ID for an existing source competitor, and SHALL report inserted, updated, skipped, and total counts for the run.

#### Scenario: Re-running the pipeline creates no duplicates

- **GIVEN** the same eligible source changes are processed twice
- **WHEN** the second run completes
- **THEN** it inserts zero new owned activities, preserves one record per source provenance key, and reports the resulting counts

#### Scenario: Competitor identity remains stable across reruns

- **GIVEN** a source competitor is already represented by an owned `cpt_` record
- **WHEN** a later pipeline run sees that same source competitor
- **THEN** it updates or reuses the existing owned competitor ID rather than creating a second competitor
