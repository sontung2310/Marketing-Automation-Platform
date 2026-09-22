# Spec Delta

## Purpose

Creates safe, visibly simulated competitor activities from validated demo templates so the activity feed can be exercised without fabricating activity for real competitors.

## ADDED Requirements

### Requirement: Simulation creates fictional-only owned activity

The system SHALL choose a requested or random fictional competitor and a compatible validated template, create an owned `CompetitorActivity` with `is_simulated = true` and `source.system = SIMULATED`, and preserve valid type-specific fields and current UTC timestamps.

#### Scenario: Requested fictional competitor is simulated

- **GIVEN** a fictional competitor and a compatible template exist
- **WHEN** simulation is requested for that competitor
- **THEN** exactly one owned activity is created for it with a distinct simulation provenance reference and `is_simulated = true`

#### Scenario: Random simulation chooses only fictional competitors

- **GIVEN** no competitor is requested and both real and fictional competitors exist
- **WHEN** simulation is requested
- **THEN** the created activity references a fictional competitor and never the real competitor

#### Scenario: Real competitor is rejected

- **GIVEN** a real competitor is requested
- **WHEN** simulation is requested
- **THEN** no activity is written and the validation error is `Simulated activity can only be created for fictional demo competitors`

#### Scenario: Each simulation event has distinct provenance

- **GIVEN** the same template is simulated twice
- **WHEN** both requests complete
- **THEN** two activities exist with different `source.ref_id` values and both remain marked simulated
