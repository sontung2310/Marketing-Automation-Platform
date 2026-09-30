# Strategy judge rubric

> Status: approved by the owner on 2026-09-30 (roadmap 4.4). Calibrated against 50 owner-scored
> runs before the first baseline; results are appended at the end of this file.

The judge scores what code cannot: whether the advice is right for Marketing Eye.
Deterministic checks already cover the schema, cited IDs, counts, channels, phrases and
refusal status, so do not re-score those. Score each dimension as an integer from 1 to 5,
using the anchors below; 2 and 4 sit between the neighbouring anchors.

Marketing Eye (Australia) is a B2B marketing agency. Its pillars are B2B growth, Brand
clarity, Content craft and Marketing leadership; its channels are LinkedIn, X and its
website. The bundle's `brand_voice` and the retrieved company record are the reference.

## Relevance: does it answer the request?

- **5**: Answers exactly what was asked: the intent, the trigger record, and every stated constraint (channel, time frame, pillar).
- **3**: Answers the request but drifts, pads, or misses one explicit constraint.
- **1**: Answers a different question, or ignores the trigger, or writes the deliverable itself (a post, email or ad) when it should hand a brief to the Execution agent.

*Example:* "What should we post on X this week?" answered with LinkedIn-length ideas relabelled as X is a 3.

## Grounding: do the claims follow from the evidence?

- **5**: Every claim, number and date traces to a retrieved record or the company context; missing or stale data is named in `data_gaps`; answers resting on demo records carry the "Based on demo data" assumption (take one point off when it is missing).
- **3**: Mostly grounded, but some generic claims are presented as findings.
- **1**: Conclusions contradict or go beyond the evidence, or facts are invented.

*Example:* a response plan that says Brightlane "is struggling" when the record only shows a price change is a 2.

## Actionability: could the team act on it tomorrow?

- **5**: Specific, prioritised actions, each with a `next_action` brief the Execution agent can follow without guessing (a justified `MONITOR` option needs no brief).
- **3**: Sensible direction but vague ("post more on LinkedIn").
- **1**: No usable action, or only restates the evidence.

For answers that correctly do not recommend, score how useful the answer is instead:

- `NEEDS_CLARIFICATION`: **5** when the question and its 2–3 options would let the user answer in one click.
- `REFUSED`: **5** when the refusal is clear and the ethical alternative is concrete.
- `INSUFFICIENT_DATA`: **5** when it states exactly what is missing and what data or next step would fill the gap.

A correct refusal or clarification is never marked down for having no recommendations.

## Marketing soundness: is it good marketing for this company?

- **5**: Applies the loaded skill's method correctly, fits Marketing Eye's positioning, ICP and pillars, and avoids race-to-the-bottom, copycat or unethical tactics.
- **3**: Generic best practice that ignores the company context, or a topic that closely copies a competitor's post.
- **1**: Harmful or unethical advice, or advice that contradicts the company's positioning.

*Example:* answering a competitor's price rise by matching it, without considering value or margin, is a 2.

## Calibration log

Calibration results are appended below by `evals.cli calibrate <run_dir> compare`.
