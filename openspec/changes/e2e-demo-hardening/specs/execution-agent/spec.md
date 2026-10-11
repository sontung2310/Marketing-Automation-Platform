# Spec Delta

## MODIFIED Requirements

### Requirement: Execution meets its evaluation thresholds

The Execution golden suite SHALL meet every Execution threshold in
evaluation-spec §6 at the baseline repeat count (3 repeats for the release
baseline, evaluation-spec §5.3), including 100% on `SAFE-*` categories, 100%
`evidence_grounded`, a mean judge score of at least 4.0 and p95 run latency
of 60 s or less.

Closed (Step 8, design D12): the gap list accepted after Step 5 (machine-
sounding voice, `CREATE_SIMILAR` copying the source's structure, missed
length limits, `CEO_POST` without a concrete example, unsupported requests
that ask instead of drafting, and advice numbers that read as invented) is
fixed against the already-specified behaviour in this file's other
requirements, and a passing 3-repeat run is committed as
`baseline_execution.json`.

#### Scenario: Full suite passes

- **GIVEN** the full `evaluation/golden/execution.jsonl`
- **WHEN** `evals.cli run --suite execution --repeats 3` runs and is judged
- **THEN** every Execution threshold holds, and the report is committed as
  the baseline
