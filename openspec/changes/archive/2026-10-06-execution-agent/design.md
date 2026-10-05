# Design

## Context

Step 4 left a working pattern to copy. `RunService` routes the Execution
triggers already (`routing.py`), resolves their records (`references.py`) and
dispatches to an agent function keyed by `AgentName`. `PERSISTERS` is a
registry waiting for an Execution entry. `Deliverable`, `ProposedAction` and
their repositories exist with no writers. `agents/execution/config.py` holds
the skill allowlist. The UI (Step 7) already calls
`POST /actions/{id}/approve|discard` and expects `output.final` to carry
`deliverable_id`, `proposed_action_ids` and persisted `proposed_actions`
(`frontend/src/api/types.ts`). See proposal.md for scope and the three owner
decisions.

## Goals / Non-Goals

**Goals:**

- Execution mirrors Strategy's shape (agent builder, run function, validation
  module, persister), so the two agents read alike.
- Everything code can decide deterministically (deliverable type, word count,
  schedule, payload content, originality) is decided in code, not by the
  model.

**Non-Goals:**

- Chat reference resolution (`recommendation:N`, `deliverable:last`) and the
  classifier: Step 6.4. Revisions work through the session's previous answer,
  which the run service already passes.
- `POST /runs`, SSE and `GET /actions`: Step 6.
- Marking a recommendation `IN_PROGRESS` when **Do this** runs. No spec asks
  for it yet.
- Multi-tenant action ownership: one tenant, like the MCP.

## Decisions

### D1. One shared "run, validate, repair once" loop

Strategy's `run.py` inlines the repair: run, collect problems, re-prompt once
inside the remaining turn budget, then fail. Execution needs the same loop
with different checks. Move it to `agents/common/repair.py` as one function
that takes the agent, the output type and a `problems(output) -> Problems`
callable. Strategy moves onto it with no behaviour change: its unit tests and
the live test stay green, and the Strategy suite is re-run (task 5.2). This
follows the convention of one pattern per kind of problem.
_Alternative:_ copy the loop into Execution. Rejected, because two copies
would drift.

### D2. The deliverable type is computed, then enforced

`agents/execution/types.py` holds a registry keyed by `ActivityType` (and, for
`SOCIAL_POST`, by `Channel`) → `DeliverableType`, plus fixed types for
`FROM_RECOMMENDATION` (from `next_action.deliverable_type`) and
`INFLUENCER_OUTREACH`. Code writes the expected type into the run input
("Deliverable type: BLOG_DRAFT"). A mismatch is a repair problem. Chat has no
expected type: the model chooses, and evals check it.
_Alternative:_ trust the model. Rejected, because the type is known for free.

### D3. The agent proposes the intent; code builds the payload

Strict structured output handles a free `dict` payload poorly, and the model
cannot know the `deliverable_id`. The agent-facing model is
`ActionProposal {action_type, summary, when: str | None}`, where `when` is set
only if the user named a time or date. On persistence, a registry keyed by
`ActionType` builds and validates the typed payload (agents-spec §8) from the
deliverable, the trigger record (influencer name and handle for
`create_email_draft`, recommendation ID for `add_to_content_calendar`) and
`when`. The default is the next weekday at 09:00 `Australia/Sydney`, using
`zoneinfo` with an injectable clock. agents-spec §7.2 is updated to this
shape. Persisted `ProposedAction` keeps the full payload.

### D4. Guards are pure functions with two severities

`agents/execution/guards.py` takes the output and the run's source texts and
returns problems. **Hard** problems fail the run after the one repair:
ungrounded IDs, the wrong deliverable type, and originality (12-word run or
Jaccard ≥ 0.15, word tokens lower-cased with punctuation stripped). This
means a copy is never returned. **Soft** problems survive the repair as a
`FLAG` plus a note, written by code over whatever the model reported: channel
length (a limit registry keyed by `DeliverableType`, honouring a user-given
length in `assumptions`) and competitor naming. Code also overwrites
`word_count`. Sources for originality are the trigger activity's `title` and
`content_excerpt`, plus the excerpts of any activity fetched in the run, which
covers a chat "copy their blog". Competitor names come from the trigger
record's `competitor_name` and the `competitor_name`/`name` fields in the
run's MCP results. No extra reads are needed, and agents still touch data
only through the MCP.

### D5. Trigger evidence is citable

`RunService` already adds the trigger record's ID to `retrieved_ids`. For a
`RECOMMENDATION` trigger it also adds the recommendation's evidence IDs,
since 5-C requires citing them and they were grounded when Strategy produced
them. This is generic: any trigger record with an `evidence[]` list
contributes its IDs.

### D6. The Execution persister writes all-or-nothing

`persist_execution` joins `PERSISTERS`. On `OK` it inserts the deliverable,
then its actions (built by D3). If the action insert fails, it deletes the
deliverable. It returns `{deliverable_id, proposed_action_ids,
proposed_actions: [persisted records]}`, which merges over `output.final` so
the UI gets the records it renders. Non-`OK` outcomes persist nothing.
`ProposedAction.proposed_at` is renamed `created_at` to match the other
collections and the UI type. Nothing writes the field yet.

### D7. Approval is a conditional state transition

`orchestration/actions.py` (`ActionService`) owns approve and discard. The
repository gains `transition(id, from_status, update)`: one
`find_one_and_update` filtered on `status`, so two concurrent approves cannot
both execute. Approve: validate the payload with the overrides (`422` without
any transition) → `PROPOSED → APPROVED` (or `409`) → run the connector →
`EXECUTED` with the receipt, or `FAILED` with the message. Discard:
`PROPOSED → DISCARDED` (or `409`). Unknown ID → `404`. Connectors:
`connectors/base.py` defines the `Connector` protocol
(`execute(payload) -> receipt`), and `connectors/mock/` provides one class per
`ActionType` in a registry keyed by the enum. Receipts carry `mock: true`.
`api/routes/actions.py` validates and delegates. The existing `DomainError`
handler maps `ConflictError` to `409`.
_Alternative:_ put the actions endpoints off until Step 6. Rejected by the
owner (5-D tests HTTP).

### D8. The spokesperson is a required company field

`Company.spokesperson: Spokesperson {name, role, voice_notes}`, required, so
seed validation catches its absence. The seed adds a fictional Marketing Eye
founder and CEO. The fixture `intelligence_v1` is re-snapshotted with it, so
Strategy sees the same context in evals.

`voice_notes` holds the professional-tone rules for first-person CEO posts
(owner decision 2026-10-04). Lead with an insight, not the author. Use "I"
sparingly and "we" to credit the team. Use no hype words. Keep the tone
measured and advisory. Company posts use `brand_voice` ("we" or impersonal),
and the instructions say so. Tone is judged by the brand-voice dimension
rather than a code check. A cheap code check would be fragile: counting "I"
penalises legitimate first person. The guards check only that first person
is present: a `CEO_POST` that never says "I", "me" or "my" is a soft
`channel_fit` problem. The first live run produced a fully impersonal CEO
post, which read "I sparingly" as "no I".

### D9. The eval suite is added through the existing registries

`Suite` gains `"execution"`. `SUITE_AGENT`, judge `DIMENSIONS` and
`seed_history` (output model per suite) become entries keyed by suite. New
checks join `CHECKS` behind `when(...)` guards, so they apply only to
Execution cases. Fixture `intelligence_v2` needs no Execution-only records:

- The seed blogs now carry long excerpts to copy from.
- `act_fx_inject_01` and `inf_fx_inject_01` already carry injections.
- A **Do this** case gives a Strategy answer as `session_history` and a
  trigger `ref_id` of `history:N`. The runner saves the answer as the
  session's latest Strategy run and points the trigger at recommendation N,
  which is exactly 5-C's setup.

Judge bundles also carry the spokesperson. The source excerpt is already in
the retrieved evidence.

### D10. Model

Execution uses `OPENAI_MODEL_AGENT` (`gpt-5.6-luna`), the same as Strategy.
There is no new setting.

### D11. Owner standards from calibration (2026-10-06)

The owner's first calibration scored the judge's runs stricter (mean 3.00
against 3.69; 77% agreement within ±1). Their notes change behaviour as well
as scoring:

- **Image suggestions.** `ExecutionDeliverable` and the stored `Deliverable`
  gain `image_suggestions: list[{placement, content, style}]`. A count
  registry keyed by `DeliverableType` (posts and ads 1, blogs 1–2, others 0)
  backs a contract problem, so a missing or extra suggestion is repaired
  once. The UI's deliverable card lists the suggestions below the draft.
  _Alternative:_ generate images. Rejected: no image model is in scope, and
  the owner asked only for a description.
- **Human voice.** The instructions list the machine patterns to avoid, and
  the rubric scores them under brand voice. The judge scores this rather than
  a code check: a phrase list in code would be brittle and easy to game.
- **Unsupported requests** name the supported channels and actions.
- **Rubric:** a 5 is rare (publish unchanged); a clean refusal with a pointer
  is good work; brand voice means "sounds like a person"; a missing image
  suggestion costs a point on marketing quality.

The same 50 runs are re-judged with the revised rubric for the calibration
comparison, as Strategy did on 2026-10-01. The behaviour changes land in task
4.5 and are measured by the baseline run.

### D12. Owner accepts the Execution quality gap for the PoC (2026-10-06)

Task 4.5 ran one round, by owner choice: the full suite at 1 repeat
(`execution_20261005T134207Z`, plus `execution_20261005T134948Z` for the three
`EX-REVISE` cases a fixture bug kept from starting). It holds every §6
threshold except the judge's:

| Threshold                                | Actual   | Bar  |
| ---------------------------------------- | -------- | ---- |
| pass@all overall                         | 0.92     | 0.90 |
| SAFE-\* categories, grounding, demo path | 1.00     | 1.00 |
| p95 latency                              | 27 s     | 60 s |
| **Judge mean**                           | **3.27** | 4.0  |
| **Lowest dimension** (brand voice)       | **2.86** | 3.5  |

Dimension means: relevance 3.88, marketing quality 3.22, brand voice 2.86,
originality 3.12 (calibration run: 3.30, 3.02, 2.60, 2.92). The owner
accepts the judge shortfall as a known gap for the PoC, so 5-F is met except
for the judge thresholds, and no `baseline_execution` is committed:
evaluation-spec §7 commits only a passing run.

**Known gaps, for a later Step to close:**

1. **Machine-sounding voice** (brand voice 2.86). "It's not X, it's Y"
   reversals, uniform bullet lists, a habitual closing question, and the
   brand's sample line ("make the next decision easier") reused as a closer.
   The instruction alone does not stop them. _Next:_ a soft guard that flags
   reversals and verbatim `sample_copy` lines for the repair turn.
2. **Create-similar follows the source's structure** (originality 3.12).
   Blogs and posts reword the competitor's points in the same order
   (EX-SIM-BLOG-02, EX-SIM-CEO-03, EX-SIM-SOCIAL-03). _Next:_ an outline step
   that picks a different thesis before drafting, or a structure-overlap
   check on section order.
3. **User length limits are missed** (EX-CONSTR-02: 643 words for 500;
   EX-CONSTR-04: ~240 characters for 200, while `quality_check` claimed a
   pass). _Narrowed in review:_ the agent now records `requested_length` and
   the guard enforces it, so a miss gets one repair and is reported as
   `channel_fit: FLAG` (a re-run of EX-CONSTR-02 gave 570 words, flagged
   honestly; EX-CONSTR-04 passed at 151 characters). _Still open:_ the model
   sometimes overshoots after the repair, and sometimes puts a character
   limit in `max_words`.
4. **CEO posts lack a concrete example** (EX-SIM-CEO-01, -04,
   EX-FREE-CEO_POST), and generic copy holds marketing quality at 3.22:
   vague CTAs ("Learn more", "Join us to learn how…") and template outreach.
5. **Unsupported requests sometimes ask instead of draft** (EX-UNSUP-02 asked
   a clarifying question and named no supported action).
6. **Advice numbers count as invented** (EX-FREE-BLOG_OUTLINE: "10–15 client
   questions"). Decide whether guidance quantities are claims; then fix the
   instructions or the check.

Closing the gap means a passing run at 1 repeat, committed as
`evaluation/reports/baseline_execution.json`.

**Strategy re-run (task 5.2).** After the D1 refactor and fixture v2, the
Strategy suite held every threshold except the judge mean: 3.92 against
4.0, down from the 4.06 baseline. Step 5 changed neither Strategy's
instructions nor the trend and influencer data where the scores dropped, so
the owner accepted it as run-to-run variation (2026-10-06). The committed
Strategy baseline is unchanged.

## Risks / Trade-offs

- [A 1,500-word blog plus one repair may exceed the 60 s p95] → Blog cases
  dominate p95. Measure after task 2.4. If the limit is breached, cap the
  repair to the failing section's rewrite or shorten tool use for blogs.
  Escalate only if the instructions cannot fix it.
- [Jaccard on short sources (X posts) is noisy] → With fewer than 5 source
  5-grams, only the 12-word-run rule applies. This is recorded in the
  evaluation-spec check.
- [The competitor-name scan misses aliases ("Lyfe")] → It matches the full
  name and its first word, case-insensitive. The judge's originality
  dimension backs it up.
- [The Strategy refactor (D1) could shift Strategy behaviour] → Its unit
  tests, the live test and a 1-repeat Strategy re-run must hold §6.
- [Re-snapshotting the fixture changes Strategy inputs] → Covered by the same
  Strategy re-run.

## Migration Plan

No production data. The renamed `ProposedAction` field has no stored
documents. The seed is idempotent, so re-running `seed_db.py` adds the
spokesperson.
