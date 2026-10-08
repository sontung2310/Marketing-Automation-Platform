# router eval report

Runs: 42 · Judging complete: yes · Overall: PASS

| Metric | Actual | Threshold | Result |
|---|---|---|---|
| pass_all_overall | 0.98 | 0.95 | pass |
| safe_categories | 1.00 | 1.0 | pass |
| demo_path | 1.00 | 1.0 | pass |
| p95_latency_s_max | 1.63 | 3.0 | pass |

## Categories (pass@all)

| Category | Share |
|---|---|
| RT-AMB | 1.00 |
| RT-EXE | 1.00 |
| RT-HINT | 1.00 |
| RT-OOS | 1.00 |
| RT-REF | 0.86 |
| RT-STR | 1.00 |

## Failing cases

- `RT-REF-02` (0/1): route, status — NEEDS_CLARIFICATION NONE CLARIFY: too vague without the referenced recommendation context

## Flaky cases


## Judge


## Cost and latency

Duration: p50 1.3 s, p95 1.6 s
