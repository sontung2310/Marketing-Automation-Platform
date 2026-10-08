# Strategy judge rubric

> Status: approved by the owner on 2026-09-30 (roadmap 4.4); revised on 2026-10-01 with
> the owner's standards from the first calibration; revised on 2026-10-08 for Step 7b
> (niche over generic, one card per price response), approved by the owner on
> 2026-10-08. Calibrated against 50 owner-scored runs before the first baseline; results
> are appended at the end of this file.

The judge scores what code cannot: whether the advice is right for Marketing Eye.
Deterministic checks already cover the schema, cited IDs, counts, channels, phrases and
refusal status, so do not re-score those. Score each dimension as an integer from 1 to 5,
using the anchors below; 2 and 4 sit between the neighbouring anchors.

Marketing Eye (Australia) is a B2B marketing agency. Its pillars are B2B growth, Brand
clarity, Content craft and Marketing leadership; its channels are LinkedIn, X and its
website. The bundle's `brand_voice` and the retrieved company record are the reference.

## The owner's standard

Score as Marketing Eye's owner would: a 5 is advice you would forward to the team
unchanged, and a technically correct but unremarkable answer is a 3, not a 4. These
standards come from the owner's calibration scores and override a lenient reading of
the anchors below.

1. **Quality over quantity.** One to three strong recommendations beat several where some
   are filler; five is the hard maximum. Each weak, repetitive or loosely evidenced recommendation lowers
   actionability and marketing soundness; an answer padded to reach a count scores at
   most 3 on both.
2. **Pricing moves start with the market.** For a competitor's price change or
   promotion, the sound first step is to re-evaluate the market (how Marketing Eye's
   price and value compare, what the move signals) and then weigh the options (hold,
   adjust, respond with content) with the trade-off of each, inside one recommendation.
   Jumping straight to "don't match, post about value" scores at most 3 on marketing
   soundness and actionability.
3. **Options, not orders.** Where the right move depends on the owner's priorities,
   present choices with their trade-offs rather than one directive.
4. **Answer only what was asked.** A factual question (what did a competitor do, how do
   prices compare) gets an accurate, direct answer quoting the recorded figures and
   dates. Unrequested recommendations add nothing; padding them in scores at most 3 on
   relevance. A short, complete, accurate direct answer is a 5.
5. **No advice without data.** When the data cannot answer the request, the best answer
   says plainly what cannot be verified and what is missing, and stops. Recommendations
   stretched from unrelated records score at most 2 on relevance and grounding.
6. **Claims of absence need a search.** "I couldn't identify X" is right only when the
   agent searched for X (the evidence shows the matching tool results). Concluding that
   something does not exist without searching is a false `INSUFFICIENT_DATA`: score
   every dimension at most 2.
7. **Ask before assuming.** An ambiguous request (a single word, an unnamed competitor)
   needs a clarifying question. Answering it with a full plan instead scores at most 1
   on relevance and at most 2 on every other dimension.
8. **Justify choices.** Say why a channel, format or priority was chosen (for example,
   why LinkedIn leads next week). An unexplained choice costs a point on actionability.
9. **Niche over generic.** Each recommendation should read like a senior strategist's
   call: it combines at least two signals (several competitors' moves, or a move and a
   trend or influencer) into one insight, names a specific audience, and says what white
   space no cited competitor occupies and why Marketing Eye can own it. Advice any agency
   could give ("post more on LinkedIn", "create thought leadership") scores at most 3 on
   marketing soundness and actionability, however well grounded. Signals cited only to
   reach two, without a real link between them, score at most 2 on grounding.

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

A correct refusal, clarification or insufficient-data answer is never marked down for
having no recommendations. A wrong one (see the owner's standard, items 5–7) is capped
as stated there.

## Marketing soundness: is it good marketing for this company?

- **5**: Applies the loaded skill's method correctly, fits Marketing Eye's positioning, ICP and pillars, and avoids race-to-the-bottom, copycat or unethical tactics.
- **3**: Generic best practice that ignores the company context, or a topic that closely copies a competitor's post.
- **1**: Harmful or unethical advice, or advice that contradicts the company's positioning.

*Example:* answering a competitor's price rise by matching it, without considering value or margin, is a 2. Answering it with "don't match; post about our value" and no market re-evaluation or options is a 3.

## Calibration log

Calibration results are appended below by `evals.cli calibrate <run_dir> compare`.
- 2026-10-01: first pass with the 2026-09-30 rubric, same 50 runs: agreement within ±1 = 71% (FAIL; the judge averaged 4.29 against the owner's 3.57). The owner's notes became "The owner's standard" above, and fresh judges re-scored the same runs.
- 2026-10-01: 50 runs scored by both the owner and the judge, agreement within ±1 = 91% (PASS, needs 80% over 50)
