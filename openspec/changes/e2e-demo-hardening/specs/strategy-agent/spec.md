# Spec Delta

## MODIFIED Requirements

### Requirement: Strategy meets its evaluation thresholds

The Strategy suite SHALL meet every Strategy threshold in evaluation-spec §6
at the baseline repeat count (3 repeats for the release baseline,
evaluation-spec §5.3), including p95 run duration of 45 seconds or less, and
the passing report SHALL be committed as the baseline.

Closed (Step 8, design D9): the gap list accepted after Step 7b (price
responses that don't weigh ≥2 options against each other, padded second
signals, focus drift, incomplete follow-ups, and white space asserted
rather than shown) is fixed against the already-specified behaviour in this
file's other requirements, and a passing 3-repeat run is committed as
`baseline_strategy.json`.

#### Scenario: Full suite passes

- **GIVEN** the approved `strategy.jsonl` and fixture `intelligence_v2`
- **WHEN** the suite runs at 3 repeats and the Claude judge scores it
- **THEN** every Strategy threshold holds and `baseline_strategy.json` is
  committed
