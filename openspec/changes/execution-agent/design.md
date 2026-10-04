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
penalises legitimate first person.

### D9. The eval suite is added through the existing registries

`Suite` gains `"execution"`. `SUITE_AGENT`, judge `DIMENSIONS` and
`seed_history` (output model per suite) become entries keyed by suite. New
checks join `CHECKS` behind `when(...)` guards, so they apply only to
Execution cases. The fixture gains `act_fx_*` blog, social and executive posts
with long excerpts, `rec_fx_*` recommendations in a seeded Strategy session,
and an `inf_fx_*` influencer with an injected bio. Judge bundles also carry
the source excerpt and the spokesperson.

### D10. Model

Execution uses `OPENAI_MODEL_AGENT` (`gpt-5.6-luna`), the same as Strategy.
There is no new setting.

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
