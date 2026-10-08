# intelligence-db-foundation Specification

## Purpose

Provides a typed, tenant-scoped owned Intelligence DB with deterministic demo data so later pipelines, MCP tools, and agents can rely on stable normalized records and safe reruns.

## Requirements

### Requirement: Owned records conform to the data contract

The system SHALL accept and persist owned records only when their collection fields, enum values, prefixed identifiers, tenant ownership, provenance, timestamps, and collection-specific invariants conform to `docs/data-contract.md` §§2–3.

#### Scenario: Invalid owned record is rejected

- **GIVEN** an owned record with an unknown enum value, missing tenant identifier, malformed prefixed ID, or invalid provenance
- **WHEN** the record crosses the persistence boundary
- **THEN** validation fails with a structured error and no MongoDB write is attempted

#### Scenario: Valid owned record is returned as typed data

- **GIVEN** a record satisfying its collection contract
- **WHEN** a repository reads it from the owned database
- **THEN** the result contains the documented fields and enum values without exposing an untyped Mongo document

### Requirement: Owned repositories and indexes are tenant-safe and idempotent

The system SHALL expose typed access to every owned collection through repositories, keep all owned Mongo queries within the repository layer, and create the documented indexes repeatedly without error. The provenance key `(source.system, source.ref_id)` SHALL be unique for collections that carry provenance.

#### Scenario: Index setup can be repeated

- **GIVEN** an empty or already indexed `marketing_automation` database
- **WHEN** application startup or seed setup runs index creation
- **THEN** all required indexes exist, including the feed query indexes and unique provenance index, and the operation succeeds on every run

#### Scenario: Duplicate provenance is not inserted

- **GIVEN** two records with the same `source.system` and `source.ref_id` in a provenance-bearing collection
- **WHEN** the second record is upserted
- **THEN** it updates the existing logical record rather than creating a duplicate

### Requirement: Seed data meets the documented demo minimums

The seed dataset SHALL contain realistic dated records and satisfy every minimum in `docs/data-contract.md` §5: company context, real and fictional competitors, activity-type and channel coverage, trends, and simulation templates. The seed SHALL contain no influencers: influencers come only from DCT (owner decision, 2026-10-07), and running the seed SHALL delete any owned influencer with `source.system = MOCK_SEED`. Every seeded record SHALL be marked `is_mock: true`; fictional competitor URLs SHALL use `.example`; adversarial content SHALL not be present.

#### Scenario: Seed validation reports complete coverage

- **GIVEN** the committed seed files
- **WHEN** the seed validation path runs
- **THEN** it reports success only when all §5 minimum counts, enum coverage, channel coverage, provenance fields, mock flags, dates, and URL rules pass

#### Scenario: Seed data stays non-production

- **GIVEN** a seeded fictional competitor or simulated template
- **WHEN** its records are inspected
- **THEN** fictional URLs use `.example`, records are marked mock, and no source database is modified

#### Scenario: Seeding removes mock influencers

- **GIVEN** a database holding `MOCK_SEED` and `DCT` influencers
- **WHEN** the seed script runs
- **THEN** no `MOCK_SEED` influencer remains and every `DCT` influencer is unchanged

### Requirement: Seed execution is safe to rerun and observable

The seed command SHALL support the configured owned database, a write-free validation/dry-run mode, and an idempotent upsert mode that reports inserted, updated, skipped, and total counts. Running it twice against the same empty-to-seeded database SHALL leave identical counts and no duplicate provenance keys.

#### Scenario: Two seed runs converge

- **GIVEN** an empty `marketing_automation` database
- **WHEN** the seed command runs twice with the same files
- **THEN** the second run inserts no new logical records, counts match the first run, and every §5 minimum remains satisfied

#### Scenario: Dry run does not write

- **GIVEN** a configured MongoDB URI and the seed files
- **WHEN** the command runs in validation or dry-run mode
- **THEN** it validates the files and prints the planned counts without creating or modifying owned collections

### Requirement: The company context names a spokesperson

The company context SHALL carry a `spokesperson` with a `name`, a `role` and
`voice_notes`, returned by `get_company_context`, so CEO posts have a
first-person voice. The Marketing Eye seed SHALL provide a **fictional**
spokesperson (owner decision 2026-10-04) and SHALL NOT name a real person.

#### Scenario: The seeded spokesperson is served

- **GIVEN** the seeded database
- **WHEN** `get_company_context` is called
- **THEN** the result includes a spokesperson with a name, a leadership role
  and voice notes, and the seed validation fails if it is missing
