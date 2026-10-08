# Design: Strategy synthesis and real influencers

## Context

- Strategy runs are keyed by `Intent` (`agents/common/intents.py`); UI
  triggers map to `(agent, intent)` in the `TRIGGER_ROUTES` registry
  (`orchestration/routing.py`), and `references.py` resolves each trigger's
  `ref_id` through a registry keyed by `TriggerKind`.
- Post-validation (`agents/strategy/validation.py`) checks the output against
  `context.retrieved_ids`, which `agents/common/mcp.py` fills from every MCP
  result. A failure triggers one repair re-prompt, then `INVALID_OUTPUT` or
  `UNGROUNDED_OUTPUT`.
- `persistence.persist_strategy` calls
  `recommendations.supersede_open(session_id, keep_run_id)`. `IN_PROGRESS`
  and `DONE` exist in `RecommendationStatus` but nothing sets them.
- The DCT source (`pipelines/sources/dct.py`) sorts by score then `_id`,
  with `DCT_CANDIDATE_LIMIT = 25`. The live database holds 10 DCT and
  20 `MOCK_SEED` influencers; the seed's relevance scores reach 0.95 and
  outrank DCT's 0.62–0.70.
- The eval harness shifts fixture dates to the run time
  (`evals/fixture.py`), so a now-anchored window is deterministic in evals.

## Goals / Non-Goals

**Goals:** one intent and one code path for every "what should we do
overall" run; the niche rule enforced in code where code can check it and
in the rubric where it cannot; real influencer data only.

**Non-Goals:**
- No new MCP tool: the existing tools already take `since_days`, `limit`
  and filters.
- No topic classification for DCT influencers; keywords keep not affecting
  the table (owner decision, Q10).
- No automatic synthesis on new activity.
- No influencer refresh schedule beyond the existing pipeline runner.

## Decisions

### D1. One new intent, `STRATEGY_SYNTHESIS`, with an optional focus

Add `Intent.STRATEGY_SYNTHESIS`, `TriggerKind.COMPANY` and
`TriggerAction.GENERATE_STRATEGY`. `TRIGGER_ROUTES` maps:

| Trigger | Intent | Focus |
|---|---|---|
| `COMPANY` + `GENERATE_STRATEGY` | `STRATEGY_SYNTHESIS` | none |
| `FEED_ACTION` + `RESPONSE_PLAN` | `STRATEGY_SYNTHESIS` | the activity |
| `TREND` + `USE_TREND` | `STRATEGY_SYNTHESIS` | the trend |
| `FEED_ACTION` + `WHY_IT_MATTERS` | `WHY_IT_MATTERS` (unchanged) | — |

`references.py` gains a `COMPANY` resolver that accepts only the current
company's ID and returns the company record; the run input then has no
focus. For the two focused triggers the resolved record already reaches the
agent as the trigger context; the synthesis instructions treat it as the
focus.

The chat router's Strategy intents are unchanged: `RESPONSE_PLAN` and
`TOPIC_RECOMMENDATION` stay as router labels and keep their instruction
rows, but those rows now follow the same count, niche and price rules.

*Alternatives:* (a) a separate `focus_id` field on `POST /runs`. That adds an
API field for something the trigger already carries. Rejected. (b) Keep
`RESPONSE_PLAN` as its own intent with new limits. That keeps two paths that
produce the same panel set. Rejected.

### D2. Output fields `insight` and `audience` on `Recommendation`

`Recommendation` gains `insight: str` and `audience: str`, both persisted on
the `recommendations` record and returned by `GET /recommendations`.
`MONITOR` may leave them empty. The strategy output schema stays one
Pydantic model, so the SDK's structured output enforces presence; the
length caps (240 and 80) are applied by `normalise()`, like the title cap.

`white_space` is folded into `insight` (owner decision, Q17).

### D3. The niche rule in post-validation

`contract_problems()` gains, for each non-`MONITOR` recommendation:

- at least 2 distinct evidence IDs with kind `activity`, `trend` or
  `influencer`;
- when all of them are activities, at least 2 distinct competitors;
- non-empty `insight` and `audience`;

and, for the whole output, at most 5 recommendations.

For the competitor check, `agents/common/mcp.py` records
`context.activity_competitors: dict[str, str]` (activity ID → competitor
ID) from the same MCP payloads it already walks for `retrieved_ids`. A
previous-answer ID with no known competitor counts as its own competitor,
so the check never fails on missing metadata.

These are the same repair-then-`INVALID_OUTPUT` path as the existing
contract problems, so no new error code.

*Alternative:* let the judge enforce it. A judge miss would let single-signal
cards into the panel. Rejected; the judge scores quality, code enforces
shape.

### D4. The expert method lives in the instructions; skills add depth

`instructions.md` gains a `# Strategy synthesis` section and a rewritten
*Advice quality* section, distilled from `marketing-ideas`,
`marketing-psychology` and standard strategy practice:

1. **Find convergence.** Look for two or more independent signals pointing
   the same way: competitors crowding one theme, a rising trend no
   competitor answers, an influencer audience that matches an ICP segment.
2. **Map the white space.** For the theme, note what each cited competitor
   is doing and the angle none of them takes.
3. **Check the right to win.** Tie the play to Marketing Eye's positioning,
   services and pillars (circle of competence); drop plays it cannot own.
4. **Name the audience and the job.** A specific segment and the job they
   hire marketing for (jobs-to-be-done), not "B2B companies".
5. **Name the lever.** The psychological mechanism that makes it work
   (authority, social proof, pratfall, loss aversion, reciprocity…), used
   ethically.
6. **Think one move ahead.** Second-order effects and how competitors may
   respond; for price moves, weigh hold, adjust and value response in one
   card.
7. **Choose.** Opportunity cost: keep the 1–3 plays with the best payoff for
   effort; more only when each is clearly distinct and strong.

The insight template is "Because <signal A> and <signal B>, <white space> is
open; Marketing Eye can own it because <advantage>." The intent table gains
the `STRATEGY_SYNTHESIS` row (company context → `summarize_competitor_activity`
(30 days) → `search_competitor_activity` as needed → `search_trends` →
`search_influencers` → focus record if any). The "widen `since_days`" rule
stays for direct questions but not for synthesis, which stays inside 30
days. `marketing-psychology` is vendored at the pinned commit with
`update_skills.py --commit <same sha> --skills …` and added to the Strategy
allowlist only.

*Alternative:* force a skill load each run. That costs a turn and tokens on
every run for text the distilled method already covers. Rejected.

### D5. One company-wide set; `DONE` after a successful recommendation run

`supersede_open` changes from session scope to company scope. A
recommendation reaches its company through its session, so it marks
`{session_id ∈ the company's sessions, status: OPEN, run_id ≠ keep_run_id}`
`SUPERSEDED`, served by the existing `{session_id, status}` index. It is
called only when the run persisted at least one recommendation; a run
without any now keeps the set.

`persist_execution` sets the trigger recommendation `DONE` when the run
persisted a deliverable and the run's trigger context is a recommendation
(the button or a resolved `#N`). One repository method,
`mark_done(rec_id)` (the trigger was already resolved for the company), guarded on `status: OPEN` so a
superseded recommendation stays superseded.

### D6. Influencers: top 10, followers tiebreak, avatar, prune

- `DCT_CANDIDATE_LIMIT = 10`; sort
  `[("evaluation.latest_final_score", -1), ("profile.followers", -1), ("_id", 1)]`.
  Mongo sorts a missing follower count lowest in descending order, which
  matches the spec.
- `DctCandidate` and `Influencer` gain `avatar_url: str | None`.
- After upserting, the pipeline deletes `source.system = DCT` influencers of
  the company whose `source.ref_id` is not in the selected set, and reports
  the count.
- The repository's influencer sort becomes `relevance_score` desc,
  `followers` desc, used by both the API and `search_influencers`.
- `influencers.json` is removed from the seed bundle; the writer deletes
  `MOCK_SEED` influencers instead of upserting them. The seed validator drops
  the influencer minimums. Eval fixtures keep their influencers.

### D7. UI

- `StrategyPanel` header: a **Generate strategy** button that calls
  `startRun` with the `COMPANY` trigger (the company ID comes from the
  existing company query). It is disabled, with the existing `Working`
  status pattern, while any Strategy run is in flight. The recommendations
  query is invalidated on `run.completed`, as today.
- One Strategy run at a time: the workspace context exposes
  `strategyRunning`. **Generate strategy** and every item action whose
  `agent` is `STRATEGY` (feed, trends) read it to disable themselves, so the
  rule comes from the action's agent field, not a list of action names.
- **Latest analysis** reads the latest Strategy run's `output` that the run
  stream already delivers (`answer`, `implications`, `data_gaps`); no API
  change. It lives for the page session; after a reload the cards remain and
  the block is empty until the next run.
- The card shows the `insight` (two-line clamp) and the `audience` (muted
  small line); the sheet shows both at the top. The evidence-kind registry
  already covers `Influencer` and `Company`.
- `InfluencerTable`: an `Avatar` DS primitive renders `<img loading="lazy"
  alt="">` with an `onError` swap to the existing monogram. The image uses
  token classes for size and radius. No CSP is configured, so `pbs.twimg.com`
  images load as is.

### D8. Evaluation

- `strategy.jsonl`: `ST-RESP-*` and the `USE_TREND` `ST-TOPIC` cases become
  focused synthesis cases (`recommendations.max: 5`, the focus record
  required in tools, no "≥ 1 `COMPETITIVE_RESPONSE` citing the trigger"),
  `ST-WHY-*` expect zero recommendations, and a new `ST-SYNTH` category
  (≥ 4 cases: unfocused, stale window, single-competitor bait, over-count
  bait) is added. The total stays ≥ 48. The rewritten cases go to the owner
  for approval before the run.
- `checks.py` gains `niche_signals` (the D3 rule from the case's output and
  fixture), so the suite reports it per case.
- `rubrics/strategy.md` gains an owner standard: **niche over generic**: a
  recommendation without converging signals, a named audience and a white
  space scores at most 3 on marketing soundness and actionability; a 5 reads
  like a senior strategist's call. The four dimensions are unchanged, so the
  existing calibration stays valid.
- The suite runs once (`--repeats 1`); a passing report replaces
  `baseline_strategy.*`.

### D9. Known gap: judge quality below threshold (owner decision, 2026-10-08)

One full round on the rewritten suite (run `strategy_20261008T113931Z`, 54
cases, 1 repeat) meets every evaluation-spec §6 Strategy threshold except the
judge mean: **3.87 against 4.0**. The other results:

- deterministic pass 0.96;
- safety, grounding and demo path 1.00;
- p95 26.7 s;
- dimensions: relevance 4.22, grounding 3.94, actionability 3.74,
  marketing soundness 3.56 (the lowest-dimension floor of 3.5 holds).

The owner accepted this as a known PoC gap. No new strategy baseline is
committed. The Step 4 `baseline_strategy.*` stays as the pre-7b reference
only: it was scored under the old rubric, so the two are not comparable.

Gaps to close, from the judge's rationales, with the next fix for each:

1. **Price and promotion responses argue only for holding** (ST-RESP-PRICE_CHANGE-01/02,
   ST-RESP-PROMOTION-02, ST-SYNTH-02). The instruction to name two or more
   options with trade-offs is not followed reliably. *Fix:* a fixed
   rationale shape: "Option A (…): trade-off. Option B (…): trade-off. We
   favour … because …".
2. **Padded signals**: a second citation added to satisfy the niche rule,
   with no real link between them (ST-TOPIC-04, ST-RESP-CAMPAIGN_LAUNCH-01,
   ST-RESP-PAGE_UPDATE-02, ST-SYNTH-04). *Fix:* "drop the play rather than
   pad it", with an example of a loose versus a real link.
3. **Focused runs drift from the focus**: other cards ignore the clicked
   item, and new or removed products are not compared with Marketing Eye's
   own offer (ST-RESP-NEW_PRODUCT-01, ST-RESP-PRODUCT_REMOVED-01). *Fix:*
   every card connects to the focus or the answer says why something else
   matters more; a product move is compared with Marketing Eye's services.
4. **Follow-ups do not complete their picks** (ST-MULTI-01). On "Drop #3",
   the agent kept two single-signal picks without searching, returned a
   false `INSUFFICIENT_DATA`, and leaked internal wording ("cannot be
   repaired into compliant recommendations"). *Fix:* follow-ups search for
   a second signal for kept picks, and the agent never mentions the output
   contract.
5. **White space is asserted, not shown**: plays sit close to content a
   competitor already published (ST-TOPIC-01/02/03, ST-SYNTH-01). *Fix:* the
   insight names the competitor post it differs from.
6. Smaller items:
   - **Vague factual answer:** ST-COMP-01 gave no titles, dates or prices.
   - **Why it matters restates numbers:** the ST-WHY-* answers restate
     figures and sometimes pick a looser trend than the one whose sample
     post is the trigger.
   - **Today's date is flagged as invented:** `no_invented_numbers` fails on
     today's date, which comes from the run input (ST-STALE-01). The fix
     belongs in the check, not the agent.

Closing the gap means a passing run under the current rubric, committed as
the new baseline.

## Risks / Trade-offs

- [Synthesis needs more tool calls and tokens; p95 may pass 45 s] → the
  intent row prescribes the summary tool first and `limit`-bounded searches;
  measure p95 in the eval run and trim the read plan if needed.
- [The niche rule may make the agent pad evidence to reach two signals] →
  the rubric caps "stretched" evidence at 2 on grounding; the judge sees the
  retrieved records.
- [The rubric change without recalibration may drift the judge] → the
  dimensions and anchors stay; only one owner standard is added. If the
  owner disagrees with scores in the report, recalibrate on a sample.
- [Removing mock influencers changes the live `search_influencers` results:
  no topics, no AU region] → accepted; topic and region queries return the
  no-match note and the agent says so. Eval fixtures keep topical
  influencers.
- [Company-wide supersede means a teammate's run replaces another's set] →
  intended (one set, newest wins).

## Migration Plan

1. Merge and deploy the code first, then run `seed_db.py` (deletes
   `MOCK_SEED` influencers) and `run_pipelines.py --only influencers`
   (writes the top 10 with avatars) against the shared database. Running
   them before the merge would break production: `main`'s models use
   `extra="forbid"` and would reject `avatar_url`. Pre-merge evidence uses
   the scratch database `marketing_automation_7b`.
2. Existing `OPEN` recommendations stay until the first synthesis run
   supersedes them; existing records lack `insight`/`audience`, so the
   model defaults them to empty strings on read.
3. Rollback: revert the PR and re-run `seed_db.py` to restore the seed
   influencers.
