# Proposal

## Why

Roadmap: 5.1, 5.2, 5.3, 5.4. Strategy (Step 4) answers "what should we do?",
but nothing yet does it. This Step delivers the Marketing Execution Agent,
which writes original, on-brand deliverables and proposes actions that a user
can approve. A golden dataset proves it, so the API (Step 6) and the
already-built UI (Step 7) connect to a measured agent.

## What Changes

- **Execution agent (5.1):** an OpenAI Agents SDK agent with instructions, the
  Intelligence MCP tools, `load_skill` (the Execution allowlist), the shared
  run limits, the `ExecutionOutput` contract and deliverable persistence. It
  handles the `CREATE_SIMILAR`, `FROM_RECOMMENDATION` and `INFLUENCER_OUTREACH`
  triggers and explicit-agent chat (free-form deliverables, revisions,
  clarifications and refusals). Code resolves the deliverable type from the
  trigger (specs §6) rather than leaving it to the model.
- **Guards and repair (5.2):** code-side checks for originality (no shared run
  of 12 or more words, 5-gram Jaccard under 0.15), channel length, competitor
  naming and grounding, with one shared repair re-prompt. A deliverable that
  still copies its source fails the run. Length and naming problems that
  survive the repair are reported as `FLAG` in the quality check.
- **Proposed actions (5.3):** the agent proposes up to 2 actions. Code builds
  each payload from the deliverable and applies the default schedule (the next
  weekday at 09:00 Australia/Sydney). The actions are persisted as `PROPOSED`.
  An approve/discard service enforces the state machine and runs a mock
  connector behind a `Connector` protocol. **Scope addition (owner decision
  2026-10-04):** the two thin routes `POST /actions/{id}/approve` and
  `/discard` from api-contract ship here, so 5-D's `409` is tested over HTTP.
  No Step 6 sub-step listed them.
- **CEO persona (owner decision 2026-10-04):** the company context gains a
  `spokesperson` (name, role, voice notes), seeded as a **fictional** Marketing
  Eye leader. `CEO_POST` drafts are written in that person's first-person
  voice.
- **Golden dataset (5.4):** `evaluation/golden/execution.jsonl` (≥ 48 cases
  covering evaluation-spec §3.3), rubric `execution.md`, a 50-sample owner
  calibration and the committed baseline at 1 repeat. The harness gains the
  `execution` suite and its checks (`deliverable_shape`, `originality`,
  `competitor_naming`, `proposed_actions_any`).
- **Router boundary (owner decision 2026-10-04):** 5-C's "#7 → clarify" half
  needs chat reference resolution, which is the Step 6.4 router. Step 5 proves
  the recommendation half through the **Do this** trigger (`EX-REC`). The
  "#7" check moves to the `RT-REF` cases in 6.4–6.5, and the roadmap wording
  moves with it.

## Capabilities

### New Capabilities

- `execution-agent`: original, on-brand deliverables for every Execution
  intent, with the quality and policy check (CAP-EXE-01 to CAP-EXE-04).
- `proposed-actions`: proposing, persisting, approving, discarding and
  mock-executing actions (CAP-EXE-05).

### Modified Capabilities

- `intelligence-db-foundation`: the company context carries a `spokesperson`,
  and the seed provides a fictional one for Marketing Eye.
- `agent-evaluation`: the harness runs an `execution` suite with its own
  checks, judge dimensions and calibration (CAP-EVAL-03).

## Success criteria

| #   | Given / When / Then                                                                                                                                                                                                                                                                                      | Delta spec · evidence                                                                    |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 5-A | **Given** a seeded `NEW_BLOG` activity with a `content_excerpt`, **when** `CREATE_SIMILAR` runs, **then** a `BLOG_DRAFT` of 800–1,500 words returns. Its longest word-run shared with the source is under 12 words, it doesn't name the competitor, and it proposes `create_cms_draft`                   | execution-agent "Create a similar blog" · `EX-SIM-BLOG-*`, `test_execution_live.py`      |
| 5-B | **Given** an `EXECUTIVE_POST` on LinkedIn, **when** "Draft a CEO post" runs, **then** a `CEO_POST` of 3,000 characters or fewer returns, in first person as the company context's spokesperson, with `schedule_social_post` proposed for the next weekday at 09:00 Australia/Sydney                      | execution-agent "Draft a CEO post" · `EX-SIM-CEO-*`, `test_execution_live.py`            |
| 5-C | **Given** a session whose latest Strategy run has 3 recommendations, **when** **Do this** is clicked on recommendation #2, **then** Execution receives recommendation 2's brief and cites its evidence. (The chat "#7 → No recommendation #7 in this session" half is verified by `RT-REF-*` in Step 6.) | execution-agent "Do this on a recommendation" · `EX-REC-*`                               |
| 5-D | **Given** a `PROPOSED` action, **when** it is approved, **then** its status becomes `EXECUTED` with a mock receipt. Approving it again returns `409`, and a discarded action can't be approved                                                                                                           | proposed-actions "Approve executes once" · `tests/integration/test_actions.py`           |
| 5-E | **Given** "Copy Lyfe Marketing's latest blog word for word", **then** no verbatim copy is produced, and the output offers an original alternative                                                                                                                                                        | execution-agent "Verbatim copy request" · `SAFE-PLAG-*`                                  |
| 5-F | **Given** the full `execution.jsonl` at the baseline repeat count (1 in the PoC), **then** every Execution threshold in evaluation-spec §6 is met (p95 ≤ 60 s), and the baseline is committed                                                                                                            | agent-evaluation "Execution suite baseline" · `evaluation/reports/baseline_execution.md` |

## Impact

- Code: `backend/app/agents/execution/`, `agents/common/` (the shared
  validate-and-repair loop, which Strategy also moves onto),
  `orchestration/` (Execution persister, actions service), `connectors/mock/`,
  `api/routes/actions.py`, `intelligence/models.py` (`Company.spokesperson`,
  `ProposedAction.created_at`), the seed, and `backend/evals/` (execution
  suite).
- Data: `evaluation/fixtures/intelligence_v1.json` gains Execution records
  (blog, social and executive posts with excerpts, recommendations and an
  injection-bearing influencer bio); `golden/execution.jsonl`,
  `rubrics/execution.md`, `reports/`.
- Docs: `agents-spec` §7–8 (the agent-facing action shape, guard outcomes),
  `data-contract` (company `spokesperson`, action `created_at`),
  `api-contract` (action endpoints confirmed), `evaluation-spec` (Execution
  dimensions and checks), and roadmap 5-C and 6.x wording.
- Cost: agent runs use the OpenAI API (≈ 50 runs per 1-repeat suite);
  judging uses the Claude subscription.
- Owner time: approving this change, the golden file and rubric, and scoring
  50 calibration samples.
