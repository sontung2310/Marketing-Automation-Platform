# Spec Delta

## ADDED Requirements

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
be judged on relevance, grounding, marketing soundness, brand-voice fit,
channel craft and originality. The golden file SHALL meet every
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
