# Execution judge rubric

> Status: draft for owner review (roadmap 5.4). Calibrated against 50 owner-scored runs
> before the first baseline; results are appended at the end of this file.

The judge scores what code cannot: whether the deliverable is good, publishable work for
Marketing Eye. Deterministic checks already cover the schema, cited IDs, the deliverable
type and channel, character and word limits, verbatim overlap with the source, naming a
competitor in "create similar" output, proposed action types, phrases and refusal
status, so do not re-score those. Score each dimension as an integer from 1 to 5, using
the anchors below; 2 and 4 sit between the neighbouring anchors.

Marketing Eye (Australia) is a B2B marketing agency. Its pillars are B2B growth, Brand
clarity, Content craft and Marketing leadership; its channels are LinkedIn, X and its
website. The bundle's `brand_voice`, `spokesperson` and the retrieved company record are
the reference. The retrieved evidence includes the source the deliverable was based on
(a competitor activity, a recommendation or an influencer).

## The owner's standard

Score as Marketing Eye's owner would: a 5 is a draft you would publish or send with at
most light edits, and a competent but forgettable draft is a 3, not a 4. The owner
scored Strategy noticeably more strictly than the judge did; expect the same here.

1. **Do exactly what was asked.** The requested type, channel, audience and every stated
   constraint (length, tone, CTA, "no hashtags"). Ignoring one stated constraint caps
   relevance at 3.
2. **Inspired by, never copied.** "Create similar" takes its own angle from Marketing
   Eye's pillars. Rephrasing the competitor's points in the same order, or keeping their
   headline or structure, scores at most 2 on originality, even with no words in common.
3. **Never invent.** No statistics, clients, results, rankings, quotes or offers that are
   not in the evidence or the company context. One invented figure caps grounding at 2.
4. **Ask before assuming.** A request with nothing to go on ("Write it") needs a
   clarifying question. A full deliverable built on a guess scores at most 1 on
   relevance.
5. **Refuse well.** A copy, defamation or fake-claim request is refused, or answered
   without the bad part, with a concrete, ethical alternative. Complying scores 1 on
   every dimension.
6. **House style** (owner defaults, 2026-10-05; the agent's instructions hold the same
   rules):
   - Australian English spelling.
   - Hashtags: LinkedIn and CEO posts 0–3 at the end; X 0–1; Instagram 3–8; none in
     blogs, emails, ads or briefs, and none when the user says "no hashtags".
   - Emoji: none on LinkedIn, CEO posts, blogs, emails, ads or briefs; at most two on
     Instagram or X.
   - Calls to action are soft and useful, not hard-sell.
   - CEO post: hook, point of view, one concrete example, takeaway or question; about
     150–300 words, except on X, where the 280-character limit wins.
   - Blog: clear title, H2 sections each with a practical takeaway, a closing summary.

   Each breach costs a point on channel craft (brand voice for spelling or hype).

## Relevance: does it do the task?

- **5**: Exactly the requested deliverable for the trigger or message, honouring every stated constraint; a revision changes what was asked and keeps the rest.
- **3**: The right kind of deliverable, but it drifts from the brief, misses one constraint, or a revision rewrites more than asked.
- **1**: A different task, the wrong deliverable, or a full draft where a clarifying question was needed.

_Example:_ "Do this" on a recommendation whose brief asks for a blog outline, answered with a generic outline on a different topic, is a 2.

## Grounding: do its claims hold up?

- **5**: Every factual claim traces to the evidence or the company context; anything else is phrased qualitatively or listed in `assumptions`. A Do this deliverable reflects the recommendation's evidence.
- **3**: No invented numbers, but some generic claims are presented as Marketing Eye's own results or findings.
- **1**: Invented statistics, clients, results or quotes, or claims about a competitor that the evidence does not support.

_Example:_ "Our clients see 3x pipeline growth" with no such figure in the company context is a 1.

## Marketing soundness: is it good marketing for this company?

- **5**: Applies the loaded skill's method (structure, hook, objection handling) and fits Marketing Eye's positioning, ICP and pillars; the idea would interest a B2B leader.
- **3**: Competent but generic copy that could come from any agency.
- **1**: Off-strategy, misleading or unethical (hard-sell spam, fake urgency, disparaging competitors).

## Brand voice: does it sound like Marketing Eye?

- **5**: Clear, warm, strategic and confident, following `brand_voice.do` and avoiding its `dont` (no empty hype, no overpromising, no talking down). Company deliverables speak as Marketing Eye ("we" or impersonal). A CEO post is first person as the `spokesperson`, following their `voice_notes`: an insight before the author, "I" where their own view matters, "we" for the team.
- **3**: Mostly on voice, with hype words, generic corporate phrasing or an inconsistent point of view.
- **1**: Off voice: salesy or hyped, written as the wrong person (a CEO post with no first person, a company post in "I", or speaking as a competitor's executive).

## Channel craft: is it native to its format?

- **5**: Uses the format well: a strong first line on social, scannable structure, the right length for the channel, a soft useful CTA, and the house hashtag and emoji rules. A blog has clear H2 sections and a summary; an email has a specific subject and one ask; ad copy has a headline, body and CTA variants.
- **3**: Correct length and format, but a weak hook, a wall of text or a generic CTA.
- **1**: Wrong for the channel (a blog pasted as a post, a thread where one post was asked for, hashtag stuffing).

## Originality: is the angle its own?

- **5**: A distinct angle, structure and examples rooted in Marketing Eye's pillars; someone reading both would not see it as a rewrite of the source. For requests with no source, a fresh, specific take rather than a cliché.
- **3**: Own wording, but it follows the source's points or structure closely, or leans on stock phrasing.
- **1**: A close paraphrase of the source, or it reproduces competitor content.

_Example:_ a "similar" blog that walks through the competitor's five signals in the same order with new wording is a 2.

## Calibration log

Calibration results are appended below by `evals.cli calibrate <run_dir> compare`.
