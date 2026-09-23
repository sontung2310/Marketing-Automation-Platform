# Spec Delta

## Purpose

Provides a pinned, reviewable marketing-skill catalogue that both agents can
read through typed, allowlisted and per-run-bounded tools without accessing
arbitrary files or external systems at runtime.

## ADDED Requirements

### Requirement: The skill catalogue is pinned, complete and parseable

The system SHALL contain exactly the 12 skills listed in
`docs/agents-spec.md §4.1`, pinned to one upstream source commit and recorded
with a deterministic content hash for each skill. Each skill SHALL preserve its
upstream `SKILL.md`, references and evals content, and SHALL parse to a folder-
matching non-empty `name` and a non-empty `description`.

#### Scenario: All vendored skills load with valid metadata

- **GIVEN** the committed skill catalogue and its lockfile
- **WHEN** the loader starts and validates the catalogue
- **THEN** all 12 allowlisted skill folders load successfully, each parsed
  `name` matches its folder, and each has a non-empty description

#### Scenario: A hand-edited skill fails integrity verification

- **GIVEN** one committed skill file differs from the hash recorded in the
  lockfile
- **WHEN** the maintenance check runs in CI with `--check`
- **THEN** it exits non-zero and identifies the skill and hash mismatch

### Requirement: Skill content and references are loaded safely

The loader SHALL parse YAML frontmatter at the skill boundary, return the
skill body or one reference file within that skill's directory, and append the
product-context note directing the agent to `get_company_context`. It MUST
reject missing or malformed metadata, unknown skills, missing references and
references that escape the skill directory. Runtime loading SHALL read only
the committed local catalogue and SHALL not call MongoDB, an MCP server or an
external network.

#### Scenario: A skill body includes the platform product-context note

- **GIVEN** a valid vendored skill with frontmatter and body content
- **WHEN** an allowed agent loads the skill
- **THEN** the response contains the parsed metadata, body and the note that
  product context comes from `get_company_context`

#### Scenario: A reference cannot escape its skill directory

- **GIVEN** an allowed agent requests `../other-skill/SKILL.md` as a reference
- **WHEN** the loader resolves the request
- **THEN** it returns a structured invalid-reference error and reads no file
  outside the requested skill directory

### Requirement: Skill tools enforce agent allowlists and run budgets

The system SHALL expose typed `list_skills` and `load_skill` tools to each
agent using the allowlists in `agents/<agent>/config.py`. `list_skills` SHALL
return only the current agent's names and descriptions. `load_skill` SHALL
return only allowlisted content, and a per-run skill-load budget SHALL reject
the fourth call with `LIMIT_REACHED` without reading another file. An
unavailable skill SHALL return a structured error stating that it is not
available to the current agent. Tool calls SHALL not raise an unhandled
exception into the agent.

#### Scenario: The Execution allowlist hides pricing

- **GIVEN** an Execution run whose allowlist excludes `pricing`
- **WHEN** the run calls `load_skill("pricing")`
- **THEN** the tool returns a structured not-available-to-this-agent error
  and does not expose the pricing content

#### Scenario: The fourth load is rejected by the run budget

- **GIVEN** a run context with three completed skill loads
- **WHEN** the run calls `load_skill` a fourth time
- **THEN** the tool returns an error with code `LIMIT_REACHED` and does not
  read or return another skill file

#### Scenario: The skill registry covers both agent allowlists

- **GIVEN** the declared Strategy and Execution allowlists
- **WHEN** the tool registry is validated
- **THEN** every allowlisted name resolves to one catalogue entry and no
  unlisted skill is exposed by either agent
