## ADDED Requirements

### Requirement: Strategy synthesises one niche set from the whole picture

A `STRATEGY_SYNTHESIS` run SHALL read the company context, competitor
activity detected in the last 30 days counted back from the run's start,
current trends and the stored influencers (influencers have no date limit),
and SHALL return at most 5 recommendations, aiming for 1–3. When the run
has a focus record (an activity or a trend from the trigger), it SHALL
retrieve that record and its answer SHALL address it, but the focus SHALL
earn a recommendation only when it belongs in the best set. Every
recommendation except `MONITOR` SHALL:

- cite at least 2 distinct external signals (activities, trends or
  influencers; the company record does not count), and when all of them are
  activities they SHALL belong to at least 2 competitors;
- carry an `audience` naming a specific segment (≤ 80 characters);
- carry an `insight` (one sentence, ≤ 240 characters) stating what the
  signals reveal together, the white space no cited competitor occupies, and
  why Marketing Eye can own it.

Post-validation SHALL reject an answer that breaks the count, signal,
`audience` or `insight` rule through the existing single repair, then fail
the run with `INVALID_OUTPUT`.

#### Scenario: Generate strategy returns a small niche set

- **GIVEN** the seeded database with activity from several competitors in
  the last 30 days and rising trends
- **WHEN** a `STRATEGY_SYNTHESIS` run starts with no focus
- **THEN** the run calls `get_company_context`, retrieves recent competitor
  activity, trends and influencers, returns 1–5 recommendations, and each
  non-`MONITOR` recommendation cites ≥ 2 external signals not all from one
  competitor and has a non-empty `audience` and `insight`

#### Scenario: A single-signal recommendation is repaired

- **GIVEN** a first answer whose recommendation cites only one trend
- **WHEN** post-validation runs
- **THEN** the agent is re-prompted once naming the rule, and if the
  repaired answer still breaks it the run fails with `INVALID_OUTPUT` and
  persists no recommendations

#### Scenario: Activity older than the window is not read

- **GIVEN** a competitor activity detected 40 days before the run
- **WHEN** a `STRATEGY_SYNTHESIS` run starts with no focus
- **THEN** that activity is not cited, and if no activity falls in the
  window the answer names the gap in `data_gaps`

## MODIFIED Requirements

### Requirement: Strategy output is structured, bounded and grounded

A Strategy run SHALL return `StrategyOutput` (agents-spec §6.2) with status
`OK`, `NEEDS_CLARIFICATION`, `REFUSED` or `INSUFFICIENT_DATA`. It SHALL call
`get_company_context` before producing output, reaching the MCP server once (a
repeated identical call in the same run is answered from the run's cache), and SHALL respect the
run limits (16 turns, 12 MCP calls, 3 skill loads). Every cited evidence ID
SHALL have been returned by a tool in the same run, or be the trigger record's
ID (resolved for the company and given in the input) or an ID the session's
previous successful answer cited; if not, the system SHALL
re-prompt once naming the unknown IDs and SHALL fail the run with
`UNGROUNDED_OUTPUT` if the repair still cites them. A run SHALL return at
most 5 recommendations. Recommendation ordinals
SHALL be unique and contiguous from 1, every recommendation except `MONITOR`
SHALL carry a `next_action`, an `audience` and an `insight`, and successful
recommendations SHALL be persisted in ordinal order with those fields.

#### Scenario: Response plan for a price change

- **GIVEN** a seeded `PRICE_CHANGE` activity from Brightlane
- **WHEN** a `STRATEGY_SYNTHESIS` run starts with that activity as its focus
- **THEN** the run calls `get_company_context` then
  `get_competitor_activity` with that activity's ID, returns at least one
  implication comparing Marketing Eye's own price and value with the change,
  returns at most 5 recommendations, and any recommendation responding to
  the price change weighs its options and their trade-offs in its rationale

#### Scenario: Topic recommendations are persisted

- **GIVEN** the chat message "What should we post about next week?" sent to
  Strategy
- **WHEN** the run completes
- **THEN** 1–5 `CONTENT_TOPIC` recommendations return, each citing at least
  two `trd_` or `act_` IDs that exist in the database, persisted with
  ordinals 1..n and their `audience` and `insight`

#### Scenario: An uncited ID is repaired or fails the run

- **GIVEN** a first answer that cites an ID no tool returned in the run
- **WHEN** post-validation runs
- **THEN** the agent is re-prompted once with the unknown IDs, and if the
  repaired answer still cites one, the run fails with `UNGROUNDED_OUTPUT`
  and persists no recommendations

### Requirement: Follow-ups build on the previous answer

A Strategy run in a session that already has a successful answer SHALL
receive that answer (labelled as untrusted data), and the evidence IDs it
cited SHALL count as retrieved for the new run, since they were grounded
when first cited (owner decision, 2026-09-30). When any Strategy run
persists recommendations, every other `OPEN` recommendation of the company,
from any session, SHALL become `SUPERSEDED`, so the Strategy panel always
shows one set: the newest (owner decision, 2026-10-07). A failed run, or a
run that returns no recommendations, SHALL NOT replace the set or the
session's last answer.

#### Scenario: Drop a recommendation

- **GIVEN** a session whose last Strategy run recommended three items
- **WHEN** the user sends "drop #3" to Strategy in that session
- **THEN** the new run may cite the previous run's evidence without
  re-fetching it, returns the remaining recommendations, and the previous
  run's recommendations are `SUPERSEDED`

#### Scenario: A new set replaces another session's set

- **GIVEN** `OPEN` recommendations persisted by a run in session A
- **WHEN** a Strategy run in session B persists recommendations
- **THEN** session A's recommendations are `SUPERSEDED` and only session B's
  set is `OPEN`

#### Scenario: A factual answer keeps the set

- **GIVEN** `OPEN` recommendations from an earlier run
- **WHEN** a Strategy run answers a factual question with no
  recommendations
- **THEN** the earlier recommendations stay `OPEN`

### Requirement: Strategy advice is focused and asked for

Strategy SHALL return only as many recommendations as the evidence strongly
supports, aiming for 1–3 and never more than 5, and SHALL NOT pad to reach
a count (owner decisions, 2026-10-01 and 2026-10-07). Each recommendation
SHALL be niche: a specific audience, a non-obvious insight from converging
signals, and a play no cited competitor is making, rather than generic
advice such as "post more on LinkedIn". It
SHALL answer a factual question (what a competitor did, how prices compare,
which trends are rising) directly, quoting recorded figures and dates, with no
recommendations unless the user asks what to do. A `WHY_IT_MATTERS` run SHALL
return implications and an answer with no recommendations. An
`INSUFFICIENT_DATA` answer
SHALL carry no recommendations, and post-validation SHALL reject one that
does. The agent SHALL NOT claim that something does not exist without having
searched for it in the run. For a competitor's price change or promotion, it
SHALL first compare the move with Marketing Eye's own prices and value, and
any recommendation responding to it SHALL be one card whose rationale weighs
the options (for example hold, adjust the offer, respond with value) and
their trade-offs rather than a single directive. Each
recommendation's rationale SHALL say why its channel or format was chosen.

#### Scenario: A factual question gets a direct answer

- **GIVEN** the chat message "How do Kestrel's recent pricing moves compare
  with Brightlane's?"
- **WHEN** the run completes
- **THEN** the answer quotes the recorded before and after prices and the
  output has no recommendations

#### Scenario: No data, no advice

- **GIVEN** the chat message "What's trending on TikTok for our audience?"
  and no TikTok data
- **WHEN** the run completes
- **THEN** the answer names the gap and the output has no recommendations

#### Scenario: Absence needs a search

- **GIVEN** the eval fixture `intelligence_v1` and the chat message "Suggest
  influencers for AI search content that fits our Australian audience."
- **WHEN** the run completes
- **THEN** the run has called `search_influencers`, and the answer names
  Australian AI search creators found in the data rather than reporting
  that none exist

#### Scenario: Why it matters explains without recommending

- **GIVEN** a seeded `NEW_BLOG` activity
- **WHEN** a `WHY_IT_MATTERS` run starts for it
- **THEN** the output has 2–3 implications, an answer, and no
  recommendations, and the company's `OPEN` recommendations are unchanged
