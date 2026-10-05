# Spec Delta

## ADDED Requirements

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
