# agent-evaluation Specification

## Purpose
Measures agent behaviour on frozen data with deterministic checks in code and
rubric judging performed by Claude, so prompt, skill or model changes are
judged by the same cases every time.

## Requirements

### Requirement: Cases run against a frozen fixture and the real agent

The harness SHALL load a versioned fixture into a throwaway database, run the
real agent against a real MCP server over it, and run each case the requested
number of times. It SHALL apply every applicable deterministic check from
evaluation-spec §5.1 and record per-run tool calls, cited IDs, token usage and
duration. Golden cases SHALL follow the evaluation-spec §4 schema and
reference only IDs present in their fixture version.

#### Scenario: A grounded case passes its checks

- **GIVEN** fixture `intelligence_v1` and a golden case whose trigger points
  at a fixture activity
- **WHEN** the harness runs it
- **THEN** the report records each deterministic check's result, and
  `evidence_grounded` fails if any cited ID was not returned by a tool or is
  absent from the fixture

#### Scenario: A case referencing a missing fixture ID is rejected

- **GIVEN** a golden case whose trigger `ref_id` is not in its fixture
- **WHEN** the dataset is loaded
- **THEN** loading fails and names the case and the missing ID before any
  agent runs

### Requirement: Claude performs the rubric judging

The harness SHALL write a judge bundle for every run whose output is
schema-valid: the case, the output, the evidence records retrieved, the
company brand voice and the reference notes. Rubric scores (1–5 per
dimension, with a one-sentence rationale) SHALL be produced by Claude
subagents in a Claude Code session following the suite rubric, never seeing
other scores, and SHALL be validated against a score schema before the
report uses them. The report SHALL show whether judging is complete.

#### Scenario: Scores merge into the report

- **GIVEN** a finished eval run and a complete, schema-valid score file
  produced by the Claude judge
- **WHEN** the report is built
- **THEN** it shows the per-dimension means, the three lowest-scoring cases
  with rationales, and threshold pass/fail for judge metrics

#### Scenario: Missing scores are visible

- **GIVEN** a finished eval run with no score file, or one missing runs
- **WHEN** the report is built
- **THEN** the judge metrics are marked incomplete and the report cannot be
  committed as a baseline

### Requirement: The judge is calibrated against human scores

Before the first baseline of a suite, the product owner SHALL score 50
sampled runs, and the Claude judge SHALL agree within ±1 on at least 80% of
dimension scores. The calibration result SHALL be recorded in the suite's
rubric file.

#### Scenario: Calibration gate

- **GIVEN** 50 owner-scored runs and the judge's scores for the same runs
- **WHEN** agreement is computed
- **THEN** a baseline may be committed only if agreement within ±1 is at
  least 80%, and the rubric records the agreement figure and date

### Requirement: The harness runs the Execution suite

The harness SHALL run an `execution` suite against the real Execution agent
and MCP over the frozen fixture, with the same loader, throwaway database,
judge bundles, calibration gate and report as Strategy. It SHALL apply the
Execution checks from evaluation-spec §5.1, including `deliverable_shape`
(type, channel, character and word limits), `originality` (against the
trigger activity's `title` and `content_excerpt`), `competitor_naming` and
`proposed_actions_any`. It SHALL seed a case's `session_history` as the
session's previous answer for either agent's output, and resolve
`rec_fx_*` recommendation triggers from the fixture. Execution bundles SHALL
be judged on four dimensions: relevance, marketing quality, brand voice and
originality (owner decision 2026-10-05; grounding is left to the
deterministic checks). The golden file SHALL meet every
evaluation-spec §3.3 minimum, with at most 30% upstream-mined cases.

#### Scenario: A copied deliverable fails the originality check

- **GIVEN** an Execution case whose trigger is a fixture `NEW_BLOG` activity
- **WHEN** a run's body shares a 12-word run with the activity's excerpt
- **THEN** the case's `originality` check fails, and the case fails

#### Scenario: Execution suite baseline

- **GIVEN** the approved `execution.jsonl` and a passing Execution judge
  calibration (≥ 80% of dimension scores within ±1 over 50 owner-scored runs)
- **WHEN** the suite runs at 1 repeat and is judged
- **THEN** the report shows every evaluation-spec §6 Execution threshold, and
  `baseline_execution.json` is written only when all of them hold
