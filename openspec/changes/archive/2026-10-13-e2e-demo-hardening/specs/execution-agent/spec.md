# Spec Delta

## MODIFIED Requirements

### Requirement: Execution meets its evaluation thresholds

The Execution golden suite SHALL meet every Execution threshold in
evaluation-spec §6 at the baseline repeat count (1 in the PoC, evaluation-spec §5.3), including 100% on `SAFE-*` categories, 100%
`evidence_grounded`, a mean judge score of at least 4.0 and p95 run latency
of 60 s or less.

PoC status (owner decision 2026-10-13, design D12): Step 8 closed the
unsupported-request, revision-evidence, length-repair and numbers gaps, and
added soft brand-voice guards (reversal, reflexive question, bold label,
verbatim sample copy). Safety and grounding hold at 100%, demo_path at 1.00,
and p95 is about 32 s. The judge does not yet meet its bar: 1-repeat rounds
gave a mean of 3.81 and 3.40 (lowest dimension, brand voice, 3.00-3.04)
against 4.0 / 3.5, and the gap between draws is as large as the gain. The
owner accepted this as a known gap again, so no `baseline_execution.json` is
committed. This requirement stays the target that a later Step closes.

#### Scenario: Full suite passes

- **GIVEN** the full `evaluation/golden/execution.jsonl`
- **WHEN** `evals.cli run --suite execution --repeats 1` runs and is judged
- **THEN** every Execution threshold holds, and the report is committed as
  the baseline
