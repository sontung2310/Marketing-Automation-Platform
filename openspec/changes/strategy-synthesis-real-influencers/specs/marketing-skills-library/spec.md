## MODIFIED Requirements

### Requirement: The skill catalogue is pinned, complete and parseable

The system SHALL contain exactly the 13 skills listed in
`docs/agents-spec.md §4.1`, pinned to one upstream source commit and recorded
with a deterministic content hash for each skill. Each skill SHALL preserve its
upstream `SKILL.md`, references and evals content, and SHALL parse to a folder-
matching non-empty `name` and a non-empty `description`.

#### Scenario: All vendored skills load with valid metadata

- **GIVEN** the committed skill catalogue and its lockfile
- **WHEN** the loader starts and validates the catalogue
- **THEN** all 13 allowlisted skill folders load successfully, including
  `marketing-psychology` in the Strategy allowlist, each parsed `name`
  matches its folder, and each has a non-empty description

#### Scenario: A hand-edited skill fails integrity verification

- **GIVEN** one committed skill file differs from the hash recorded in the
  lockfile
- **WHEN** `npm run check` runs in CI, which includes the offline `--check`
- **THEN** it exits non-zero and identifies the skill and hash mismatch
