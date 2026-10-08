## MODIFIED Requirements

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
