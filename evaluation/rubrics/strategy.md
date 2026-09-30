# Strategy judge rubric (draft)

> Status: draft for the 3-case harness check in roadmap 4.3. Task 4.4 finalises the
> anchors and examples with the owner before calibration.

The judge scores what code cannot: whether the advice is right for Marketing Eye.
Deterministic checks already cover schema, grounding IDs, counts and phrases, so do
not re-score those. Score each dimension as an integer from 1 to 5.

## Relevance: does it answer the request?

- **5**: Answers exactly what was asked (intent, channel, time frame, trigger), nothing padded.
- **3**: Answers the request but drifts, or misses one explicit constraint.
- **1**: Answers a different question, or ignores the trigger.

## Grounding: do the claims follow from the evidence?

- **5**: Every claim and number traces to a retrieved record or the company context; gaps are named in `data_gaps`.
- **3**: Mostly grounded, with some generic claims presented as findings.
- **1**: Conclusions contradict or go beyond the evidence, or invented facts.

## Actionability: could the team act on it tomorrow?

- **5**: Specific, prioritised actions with a clear `next_action` brief an Execution agent can follow.
- **3**: Sensible direction but vague ("post more on LinkedIn").
- **1**: No usable action, or only restates the evidence.

## Marketing soundness: is it good marketing for this company?

- **5**: Applies the loaded skill's method correctly, fits Marketing Eye's positioning, ICP and pillars, avoids race-to-the-bottom or unethical tactics.
- **3**: Generic best practice that ignores the company context.
- **1**: Harmful or unethical advice, or advice that contradicts the company's positioning.

## Calibration log

Calibration results are appended below by `evals.cli calibrate <run_dir> compare`.
