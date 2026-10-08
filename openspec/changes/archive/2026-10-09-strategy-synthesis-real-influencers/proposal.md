# Proposal: Strategy synthesis and real influencers

Roadmap: 7.10, 7.11, 7.12, 7.13, 7.14 · CAP-STR-01, CAP-STR-02, CAP-DATA-02, CAP-DATA-04, CAP-SKL-01, CAP-UI-03, CAP-EVAL-01..03

## Why

The Strategy panel fills up with one or more recommendations per competitor
move: every **Plan a response** run adds 2–4 cards, and only same-session
runs supersede each other. The owner wants the opposite: a handful of niche,
expert-level plays that combine several competitors and trends, where
quality beats quantity. Separately, the Influencers table is dominated by
20 mock seed rows that outrank the 10 real DCT candidates, and it shows no
avatars although DCT has them.

## What Changes

- **Strategy synthesis (new intent).** A **Generate strategy** button in the
  Strategy panel header starts one run that reads the company context,
  competitor activity from the last 30 days (now-anchored), current trends
  and the top 10 influencers (no date limit), and returns at most 5
  recommendations, aiming for 1–3.
- **Focused synthesis.** **Plan a response** (feed card) and **Get topic
  ideas** (trend) start the same synthesis with that record pinned as the
  focus: it is always analysed, but it earns a recommendation only if it
  belongs in the best set. **BREAKING (spec):** `RESPONSE_PLAN` no longer
  guarantees 2–4 options or a `COMPETITIVE_RESPONSE` citing the trigger.
- **Why it matters** stays an analysis: implications and an answer, **no
  recommendations**, so it never replaces the set. **BREAKING (spec):** it
  used to return 1–2 recommendations.
- **Niche is a hard rule.** Every recommendation except `MONITOR`:
  - combines at least 2 external signals (activity, trend, influencer), not
    all from one competitor, checked in post-validation;
  - names a specific `audience` (new field);
  - states one `insight` sentence (new field): the convergence of signals,
    the white space no cited competitor occupies, and why Marketing Eye can
    own it.
- **Expert method.** The Strategy instructions gain a distilled expert
  method drawn from `marketing-ideas`, `marketing-psychology` and strategy
  practice (signal convergence, white-space mapping, jobs-to-be-done,
  a named psychological lever, second-order thinking, opportunity cost).
  `marketing-psychology` is vendored as the 13th skill and allowlisted for
  Strategy, so a run can load it for depth.
- **Price moves** become one recommendation whose rationale weighs the
  options (hold, adjust, respond with value) and their trade-offs.
- **One company-wide set.** **BREAKING (spec):** any Strategy run that
  persists recommendations supersedes every other `OPEN` recommendation of
  the company, not only the session's. A successful Execution run started
  from a recommendation (**Do this** sent unedited, or `#N`) marks it
  `DONE`, which removes it from the panel.
- **Recommendation cards** show the `insight` and the `audience`; the plan
  sheet shows both above the rationale.
- **Real influencers only.**
  - The DCT pipeline stores the top **10** eligible Marketing Eye candidates
    ranked by `evaluation.latest_final_score` desc, then `profile.followers`
    desc, then `_id`, copies `profile.avatar_url`, and removes DCT records
    that fall out of the top 10.
  - **BREAKING (data):** the 20 mock seed influencers are deleted from the
    seed files and from the database by the seed script. With DCT
    unavailable the table shows its empty or error state, never mock rows.
    The mock influencers stay only in the eval fixtures.
  - The table shows each avatar as a round image, falling back to the
    monogram when there is none or it fails to load. This reverses the
    ui-spec "No avatar images" rule.
  - Tracked keywords keep their current (non-)effect on the table.
- **Evaluation.** The strategy golden dataset is rewritten for the new
  shapes (owner approves the rewritten cases), the rubric gains the niche
  standard, and the suite is re-run to the unchanged evaluation-spec §6
  thresholds; the passing report replaces the strategy baseline.

## Success criteria

| # | Scenario | Verify |
|---|---|---|
| 7b-A | **Given** the seeded database plus DCT, **when** the influencer pipeline runs twice, **then** `influencers` holds exactly the 10 DCT records ranked by score then followers, each with its `avatar_url` where DCT has one, and no `MOCK_SEED` influencer remains after `seed_db.py`. | integration test + live pipeline log |
| 7b-B | **Given** the running app, **when** the Influencers table loads, **then** it lists 10 real handles with avatars, and a row whose image is missing or fails shows the monogram. | Vitest + Playwright |
| 7b-C | **Given** the seeded database, **when** the marketer clicks **Generate strategy**, **then** a `STRATEGY_SYNTHESIS` run returns 1–5 recommendations, each non-`MONITOR` one citing ≥ 2 external signals not all from one competitor, with an `insight` and an `audience`, and the panel shows only that set. | live run against the running env |
| 7b-D | **Given** a `PRICE_CHANGE` activity, **when** **Plan a response** runs, **then** the run retrieves that activity, the answer addresses it, any recommendation about it weighs options with trade-offs in one card, and the earlier set is `SUPERSEDED` company-wide. | live run + integration test |
| 7b-E | **Given** a recommendation in the panel, **when** its brief is sent unedited and the Execution run succeeds, **then** the recommendation is `DONE` and drops off the panel. | integration test + Playwright |
| 7b-F | **Given** the approved rewritten `strategy.jsonl`, **when** the suite runs and the Claude judge scores it, **then** every Strategy threshold in evaluation-spec §6 holds and the report is committed as the baseline. | eval report |

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `strategy-agent`: synthesis intent and focus, count cap, niche rule with
  `insight` and `audience`, price moves as one card, `WHY_IT_MATTERS`
  without recommendations, company-wide supersede, and the eval baseline.
- `run-orchestration`: the `COMPANY` + `GENERATE_STRATEGY` trigger, feed and
  trend Strategy buttons routing to the focused synthesis, and `DONE` after
  a successful recommendation run.
- `influencer-pipeline`: top 10, the followers tiebreak, `avatar_url`, and
  pruning records outside the top 10.
- `intelligence-db-foundation`: the seed no longer contains influencers.
- `marketing-skills-library`: 13 skills, adding `marketing-psychology`.
- `platform-api`: influencers sorted by score then followers with
  `avatar_url`; recommendations carry `insight` and `audience`.
- `workspace-ui`: **Generate strategy**, insight and audience on cards and
  the sheet, and influencer avatars with a monogram fallback.

## Impact

- **Backend:** `agents/strategy/` (instructions, output, validation, config),
  `agents/common/intents.py`, `orchestration/routing.py`, `persistence.py`,
  `run_service.py`, `feed.py`, `intelligence/models.py` and the
  recommendations and influencers repositories, `pipelines/sources/dct.py`,
  `pipelines/influencers.py`, `pipelines/seed/` (influencers removed),
  `skills/library/marketing-psychology/` and the skills lock; `openapi.json`.
- **Frontend:** `StrategyPanel`, `RecommendationSheet`, `InfluencerTable`,
  generated API types.
- **Evaluation:** `evaluation/golden/strategy.jsonl`, `rubrics/strategy.md`,
  a new strategy baseline report; fixtures unchanged.
- **Docs:** agents-spec §4.1, §5.1, §6; data-contract §3 (recommendations,
  influencers), §4.2 and §5; api-contract (runs trigger, recommendations,
  influencers); ui-spec §3; evaluation-spec §3.2; roadmap (Step 7b).
- **Cost:** synthesis runs make more MCP calls than a single-activity run;
  p95 must stay ≤ 45 s.
