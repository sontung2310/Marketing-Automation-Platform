# Execution judge rubric

> Status: approved by the owner on 2026-10-05 (roadmap 5.4), with the golden file;
> reduced to four dimensions the same day (owner decision). Calibrated against 50
> owner-scored runs before the first baseline; revised on 2026-10-06 with the owner's
> standards from the first calibration (items 7–11). Results are appended at the end of
> this file.

The judge scores what code cannot: whether the deliverable is good, publishable work for
Marketing Eye. Deterministic checks already cover the schema, cited IDs, the deliverable
type and channel, character and word limits, verbatim overlap with the source, naming a
competitor in "create similar" output, proposed action types, phrases and refusal
status, so do not re-score those. Grounding is not scored on its own: code fails
uncited IDs and invented numbers, and an invented claim caps Marketing quality at 2
(item 3 below). Score each dimension as an integer from 1 to 5, using
the anchors below; 2 and 4 sit between the neighbouring anchors.

Marketing Eye (Australia) is a B2B marketing agency. Its pillars are B2B growth, Brand
clarity, Content craft and Marketing leadership; its channels are LinkedIn, X and its
website. The bundle's `brand_voice`, `spokesperson` and the retrieved company record are
the reference. The retrieved evidence includes the source the deliverable was based on
(a competitor activity, a recommendation or an influencer).

## The owner's standard

Score as Marketing Eye's owner would. In the first calibration the owner averaged 3.0
where the judge averaged 3.7, and gave no 5s at all; items 7–11 come from the owner's
scores and notes and override a lenient reading of the anchors below.

1. **Do exactly what was asked.** The requested type, channel, audience and every stated
   constraint (length, tone, CTA, "no hashtags"). Ignoring one stated constraint caps
   relevance at 3.
2. **Inspired by, never copied.** "Create similar" takes its own angle from Marketing
   Eye's pillars. Rephrasing the competitor's points in the same order, or keeping their
   headline or structure, scores at most 2 on originality, even with no words in common.
3. **Never invent.** No statistics, clients, results, rankings, quotes or offers that are
   not in the evidence or the company context. One invented claim caps marketing
   quality at 2.
4. **Ask before assuming.** A request with nothing to go on ("Write it") needs a
   clarifying question. A full deliverable built on a guess scores at most 1 on
   relevance.
5. **Refuse well.** A copy, defamation or fake-claim request is refused, or answered
   without the bad part. Complying scores 1 on every dimension.
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

   Each breach costs a point on marketing quality (brand voice for spelling or hype).

7. **A 5 is rare.** A 5 is a draft the owner would publish or send unchanged. A good
   draft that still needs the owner's edits is a 4 at most, and competent but
   forgettable work is a 3.
8. **It must sound like a person, not AI.** This is what brand voice means to the
   owner. Copy built from machine patterns scores at most 2 on brand voice, however well
   it matches the tone words. The patterns: stock openers ("In today's…", "Let's dive
   in"); "it's not X, it's Y" reversals and colon-then-reveal lines; reflexive groups of
   three; hype words ("game-changer", "unlock", "elevate", "seamless"); uniform bullet
   lists where prose would do; the brand's sample line reused as a hook; a closing
   question tacked on by habit. A 4 reads as a thoughtful person at Marketing Eye wrote
   it.
9. **Posts and blogs come with an image suggestion.** A social post or ad needs one
   suggested image (where it goes, what it shows, its style); a blog needs one or two,
   placed by section. A post or blog without one is incomplete: at most 3 on relevance
   and on marketing quality. Nothing is generated; a description is enough.
10. **A clean refusal or a clear question is good work.** A refusal that names the
    problem plainly scores 4 on every dimension; it does not need to draft the
    alternative. A clarifying question with options the user can pick in one click also
    scores 4.
11. **Say what is supported.** When the user asks for something the platform cannot do
    (TikTok, sending to a whole list, publishing now), the answer says so plainly _and_
    names what it can do (LinkedIn, X or Instagram scheduling, CMS drafts, email drafts,
    calendar entries). Missing the second part scores at most 2 on relevance. An email
    subject line must be specific and professional; a generic one costs a point on
    marketing quality.

## Relevance: does it do the task?

- **5**: Exactly the requested deliverable for the trigger or message, honouring every stated constraint; a revision changes what was asked and keeps the rest.
- **3**: The right kind of deliverable, but it drifts from the brief, misses one constraint, or a revision rewrites more than asked.
- **1**: A different task, the wrong deliverable, or a full draft where a clarifying question was needed.

_Example:_ "Do this" on a recommendation whose brief asks for a blog outline, answered with a generic outline on a different topic, is a 2.

## Marketing quality: is it good, channel-native marketing for this company?

- **5**: Applies a sound method (structure, hook, objection handling) and fits Marketing Eye's positioning, ICP and pillars, so a B2B leader would care. It uses its format well: a strong first line on social, scannable structure, the right length, a soft useful CTA and the house hashtag and emoji rules. A blog has clear H2 sections and a summary; an email has a specific subject and one ask; ad copy has a headline, body and CTA variants.
- **3**: Competent but generic copy that could come from any agency, or the right format with a weak hook, a wall of text or a generic CTA.
- **1**: Off-strategy, misleading or unethical (hard-sell spam, fake urgency, disparaging competitors), wrong for the channel (a blog pasted as a post, hashtag stuffing), or it invents clients, results, rankings or quotes.

For a clarifying question or a refusal, score how useful it is (item 10): a clear question with one-click options, or a refusal that names the problem plainly, is a 4.

_Example:_ a LinkedIn post with no invented figures but stock advice ("start with your customer") and a flat ending is a 3.

## Brand voice: does it sound like Marketing Eye?

- **5**: Reads as written by a thoughtful person at Marketing Eye, with no machine patterns (item 8): clear, warm, strategic and confident, plain specific sentences with varied rhythm, following `brand_voice.do` and avoiding its `dont`. Company deliverables speak as Marketing Eye ("we" or impersonal); a CEO post is Morgan Hale in first person, following the `voice_notes`.
- **3**: On tone, but with some machine patterns or generic corporate phrasing, or an inconsistent point of view.
- **1**: Reads as AI-generated throughout, salesy or hyped, or written as the wrong person (a CEO post with no first person, a company post in "I", or speaking as a competitor's executive).

_Example:_ a LinkedIn post that opens with the brand's sample line in bold, lists three parallel bullets and ends on "What's your take?" is a 2, even if every word is on-brand.

## Originality: is the angle its own?

- **5**: A distinct angle, structure and examples rooted in Marketing Eye's pillars; someone reading both would not see it as a rewrite of the source. For requests with no source, a fresh, specific take rather than a cliché.
- **3**: Own wording, but it follows the source's points or structure closely, or leans on stock phrasing.
- **1**: A close paraphrase of the source, or it reproduces competitor content.

_Example:_ a "similar" blog that walks through the competitor's five signals in the same order with new wording is a 2.

## Calibration log

Calibration results are appended below by `evals.cli calibrate <run_dir> compare`.

- 2026-10-06: first pass with the 2026-10-05 four-dimension rubric: agreement within ±1 = 77% (FAIL; the judge averaged 3.69 against the owner's 3.00, widest on brand voice and relevance). The owner's notes and scores became items 7–11 above, and fresh judges re-scored the same runs.
- 2026-10-06: 50 runs scored by both the owner and the judge, agreement within ±1 = 98% (PASS, needs 80% over 50)
