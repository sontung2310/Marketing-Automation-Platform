# Lead / implementer collaboration (Herdr)

> Pointer: AGENTS.md §4. Read this before starting or resuming a loop, in any
> role.

| Role | Agent | Owns |
|---|---|---|
| **Lead** | Claude Code, Opus 5 at the highest effort | The issue end to end: plans, briefs, reviews the proposed OpenSpec change and implementer reports, verifies every result, decides when work is done and spawns the reviewer. Owns GitHub bookkeeping (issues, labels and human queue), autopilot merging and the `.handoffs/` checkpoint. Its repository boundary and merge bar are in AGENTS.md §4. |
| **Implementer** | Codex, `gpt-5.6-terra` at `xhigh` (`~/.codex/config.toml`) | Writes the OpenSpec change from the lead's prompt, then does exactly the briefed tasks via `openspec-apply-change`: implements, checks and reports. Commits, pushes and opens the PR when the lead says so. |
| **Reviewer** | A fresh Claude subagent, spawned by the lead | An independent verdict on the PR (see "Fair review") |
| **Human** | The engineer on duty | Approves the OpenSpec change, answers escalations and merges outside autopilot. In **autopilot**, the lead merges only under the AGENTS.md §4 merge bar; the human audits asynchronously through the human queue (see "Autopilot"). |

## Setup

1. Start Herdr in a terminal (`herdr`), and in its first pane start the lead:

   ```bash
   cd ~/Project/Marketing-Automation && claude --model claude-opus-5 --effort xhigh --permission-mode auto
   ```

   The loop only runs inside a Herdr pane. Confirm with `test "$HERDR_ENV" = 1`.
   On the first run, approve the project MCP servers (`/mcp`): the loop needs
   `mongodb` and `github`.
2. The lead starts the implementer in a sibling pane:

   ```bash
   herdr pane split --current --direction right --cwd "$PWD" --no-focus   # → .result.pane.pane_id
   herdr agent start implementer --kind codex --pane <pane_id> -- \
     --approve-for-me --no-alt-screen -c sandbox_workspace_write.network_access=true
   ```

   - `--approve-for-me` sends Codex's permission requests to automatic review
     instead of pausing.
   - `--no-alt-screen` keeps Codex's output in the scrollback, where
     `herdr agent read` can reach it.
   - Network access lets Codex run `npm ci`, `uv sync` and the integration
     tests.

## The loop

1. **Brief.** The lead writes `.handoffs/<change>/brief-<n>.md`
   (gitignored), then runs
   `herdr agent prompt implementer "Read .handoffs/<change>/brief-<n>.md and do it." --wait --timeout 1800000`.
   Every brief has five parts:
   - **Context:** the issue, the OpenSpec change path if any and `Roadmap: X.Y`.
   - **Scope:** exact task IDs from `tasks.md`, if there is a change.
   - **Constraints:** AGENTS.md, `docs/coding-conventions.md`, and files to
     leave untouched.
   - **Done when:** checks to run, success-criteria scenarios to prove.
   - **Report format:** as in step 3.
2. **Implement.** For work with an OpenSpec change, the implementer works the
   scoped tasks and checks them off in `tasks.md`. For discovery or doc-only
   work, the implementer completes the written brief; there is no `tasks.md`.
3. **Report.** Every implementer turn ends with:
   - `STATUS: DONE | BLOCKED | NEEDS_DECISION`
   - tasks done
   - files changed
   - commands run, with their results
   - deviations
   - open questions

   The lead reads it with
   `herdr agent read implementer --source recent-unwrapped --lines 200`. If
   it's cut off, the lead asks for it as `.handoffs/<change>/report-<n>.md`.
4. **Verify.** The report is a claim. The lead reads `git diff`, runs
   `npm run check` and the success-criteria scenarios, and compares the result
   with `tasks.md` and the delta specs when there is an OpenSpec change;
   otherwise, it compares the result with the written brief and issue
   acceptance criteria.
5. **Follow up.** Each follow-up names the file and line, the failing output
   and the expected behaviour. Allow at most **3 rounds per task group**;
   after that, in autopilot add a summary to the human queue and stop;
   outside autopilot, escalate to the human with a summary.
6. **Finish.** When verification is green, the lead tells the implementer to
   do the following:
   - tick the roadmap box only after its scoped success-criteria scenarios
     pass and the evidence is in the PR;
   - commit with a Conventional Commit message;
   - push `feature/<step-number>-<slug>`;
   - open the PR from `.github/pull_request_template.md`, with the roadmap
     sub-step(s) and `Closes #<issue>` in the body.
7. **Review.** The lead spawns the reviewer. Every finding is either fixed
   through another loop round, or answered on the PR with a written reason.
   Once the fair review is clean, the lead tells the implementer to archive
   the OpenSpec change, if there is one, then commit and push that archive
   with any review fixes.
8. **Merge.** Outside autopilot, the human merges only under the AGENTS.md
   §4 merge bar. Autopilot follows its merge rule below.

**Blocked or stalled implementer.** On `blocked` (an approval or question
UI), the lead reads the pane and, in autopilot, records the question on the
human queue and stops; outside autopilot, it puts the question to the human. On
`timeout` or `agent_prompt_stalled`, the lead reads the pane before
re-sending, because the prompt may already have arrived.

## Fair review

The reviewer judges the PR against the spec and the standards. It doesn't
judge it against the lead's intentions or the implementer's self-assessment.

- **Fresh, minimal context.** The lead spawns the reviewer with the Agent
  tool and passes only the prompt below. It never includes its own
  conversation, the implementer's reports, or an opinion of the work.
- **Same prompt every time.** Only the four placeholders change:

  ```text
  Review PR #<n> (branch <branch>) against origin/main. Linked issue: #<issue>.
  OpenSpec change: `openspec/changes/<change>/` or `none` (discovery or doc-only work).
  Run independent passes in separate sub-agents:
  1. Spec: does the diff implement the issue's acceptance criteria and the delta
     specs, no more and no less?
  2. Standards: does it follow AGENTS.md and docs/coding-conventions.md (§11 checklist),
     including security, error handling and tests?
  3. UI (UI changes only): verify every ui-spec §8 checklist item and tick the
     matching PR checklist only after it passes.
  Report each finding as: file:line · severity (high/medium/low) · concrete failure
  scenario. Verify every finding by tracing or reproducing it before reporting.
  Report "no findings" for a pass with none. Post the result with
  `gh pr review <n> --comment --body-file <report>`.
  ```

- **Visible outcome.** The review lives on the PR, so the human sees each
  finding next to the lead's answer.

## Autopilot

Autopilot runs the loop above sub-step after sub-step through
`docs/roadmap.md`, without a human in the chat. It continues until a
**stop condition** is met. Everything below applies only in autopilot.

### Rules

These say when to skip a step, when to decide alone, and when to actually
stop.

**The lead directs and verifies; the implementer changes the repository.**
For a system-behaviour change, the implementer runs `openspec-propose` from
the lead's prompt, and the lead reviews it with follow-ups before
implementation begins.

**OpenSpec scope.** Follow AGENTS.md §3. A sub-step that is pure investigation
or documentation — inspecting source collections, rewriting a contract doc —
still goes through everything else: a GitHub issue, a
`feature/<step-number>-<slug>` branch, a PR naming its roadmap sub-step(s),
the fair review and a green **Check**. Its PR says `OpenSpec change: none`;
don't invent a change to satisfy the workflow table.

**Ticketing is just-in-time, one group at a time.** Tickets for a later step
are not cut in advance, because what an earlier step discovers changes what
they should say. Step 1's tickets are written after Step 0.4 lands, not
before.

**Grill only genuinely open behaviour.** The roadmap's success criteria are
already Given / When / Then, so tickets are cut straight from them. The
`grill-me` step is for a decision the specs haven't made, not a ceremony for
every sub-step.

**When something is open, decide — don't stop.** Pick the default most
consistent with the existing specs, record the decision in the PR, and add a
comment to the human queue below. Each entry names the decision, the rejected
alternative, the spec that made it the most consistent default, where it
landed, and how reversible it is. Silence from a human means accepted; a reply
gets folded back into the spec or the relevant doc.

**Stop only when the decision is architectural or irreversible:** the layering
in AGENTS.md §2, a data contract that later steps would have to be rebuilt
around, anything that writes to a source system, and anything that costs money
or is publicly visible.

**Verify the implementer's environment before delegating to it.** The
implementer runs its own tools, not the lead's. Before briefing Codex on work
that touches a data source, confirm the configured MongoDB command, following
any wrapper script it points at, runs with `--readOnly` and targets the same
cluster as this repo's `.env`. If either is wrong, record it on the human
queue and stop.

**Labels.** `ready-for-agent` — specified, engineering can pick it up.
`autopilot` — being worked by the loop without per-step human approval.
`needs-human` — carries a decision for the human on duty.

### Checkpoint and resume

Claude can hit its own usage limit mid-sentence, so progress is saved after
every phase, never only at the end.

- **Ground truth:** the checkboxes and `EVIDENCE-HOLD` markers in
  `docs/roadmap.md` on `main`, using the marker semantics in its header.
  Open GitHub issues and PRs with the `autopilot` label, except the standing
  human-queue issue #4, identify work in flight.
- **Checkpoint:** `.handoffs/autopilot.md` (gitignored). Rewrite it after
  every phase change. It records:
  - the current group of sub-steps, with its issue, branch and PR;
  - the phase: `ISSUE`, `SPECIFY`, `BRIEF`, `IMPLEMENT`, `VERIFY`, `PR`,
    `REVIEW` or `MERGE`;
  - the follow-up round count;
  - the paths of the last brief and report.
- **Resume:** read the checkpoint, reconcile it against the ground truth (a
  merged PR means that group is done), and continue from the recorded
  phase. When the checkpoint and GitHub disagree, trust GitHub. A resumed
  run finishes work in flight before it starts anything new.

### Per group of sub-steps

1. **Pick.** First take an open work-in-flight issue other than the standing
   human-queue issue #4. An `EVIDENCE-HOLD` sub-step's linked issue is
   ordinary queued evidence work: select it by issue rather than roadmap
   position, then remove its marker and tick its box when its evidence meets
   AGENTS.md §5. Otherwise, take the next unchecked sub-steps without an
   `EVIDENCE-HOLD` marker in roadmap order, grouped only when they're tightly
   related (usually 1–3; never across Steps). Done when the group and its
   slug are in the checkpoint.
2. **Issue.** Create one GitHub issue using
   [issue-tracker.md](issue-tracker.md) and the `to-tickets` issue template,
   without the interactive quiz. Labels: `ready-for-agent` and `autopilot`
   (create any missing label once with `gh label create`).
   The issue names the applicable Given/When/Then scenarios from its roadmap
   Step as its acceptance criteria. Done when the issue exists.
3. **Specify.** The implementer runs `openspec-propose` from the lead's
   prompt for the issue (`Roadmap: X.Y`). The lead validates it with
   `npm run openspec:check` and reviews it with follow-ups before
   implementation begins. The human reviews the delta specs in the PR
   instead. Done when validation passes and the lead has no unresolved
   follow-up.
   - **Discovery or doc-only sub-steps** (e.g. 0.3–0.4, verifying the data
     contract against the live cluster) follow AGENTS.md §3 — skip straight
     to step 4. They are still briefed to the implementer like any other
     work: Codex has its own MongoDB MCP, and the lead verifies the result by
     spot-checking the source itself rather than by doing the inspection for
     it.
4. **Brief → implement → report → verify → follow up.** Run the loop above
   on branch `feature/<step-number>-<slug>`, starting a fresh implementer
   conversation for each group (Codex's `/new`). Done when the lead's own
   verification meets AGENTS.md §5: `npm run check`, plus every applicable
   success-criteria scenario scoped to the group run against a real
   environment.
5. **PR.** Codex commits, pushes and opens the PR with `Roadmap: …`,
   `Closes #<issue>` and the `autopilot` label. If it cannot commit, push or
   open the PR, record the failure on the
   [human-queue issue #4](https://github.com/sontung2310/Marketing-Automation-Platform/issues/4)
   and stop; the lead does not take over. Done when the **Check** job is green
   on the PR.
6. **Review.** Spawn the fair reviewer. Fix each finding through another
   loop round, or answer it on the PR. Done when every finding has a fix or
   an answer, and no high-severity finding is merely answered.
7. **Merge.** Before merging, satisfy the AGENTS.md §4 merge bar. After a
   finding is fixed or its written reason is posted, resolve its review thread
   with GitHub's `resolveReviewThread` GraphQL mutation, for example:

   ```bash
   gh api graphql -f query='mutation($threadId:ID!) { resolveReviewThread(input:{threadId:$threadId}) { thread { isResolved } } }' -F threadId=<thread-id>
   ```

   Thread resolution is GitHub bookkeeping, not another review round. The lead
   then runs `gh pr merge --squash`. If any merge-bar requirement cannot be
   met, leave the PR open, record it on the
   [human-queue issue #4](https://github.com/sontung2310/Marketing-Automation-Platform/issues/4)
   and stop. After merging, sync `main` locally. The human audits merged work
   asynchronously and can revert it. Done when this group's PR is merged,
   its roadmap state is updated, and CI on `main` is green.

### Human queue

Nobody is watching the chat, so human-only items go into one standing GitHub
issue titled **"Autopilot: waiting on a human"**
([#4](https://github.com/sontung2310/Marketing-Automation-Platform/issues/4),
labels `needs-human` and `autopilot`), one comment per item. Adding an item
doesn't stop the run. Queue items include:

- decisions the spec leaves open (the lead also records the default it
  chose, in the PR);
- judge calibration (evaluation-spec §5.2) — the baseline is provisional
  until it's done;
- the demo dry-run with an outsider (8-E);
- anything that needs a credential, money or an account.

### Stop conditions

Stop the run, rewrite the checkpoint with the reason, and post a summary as
a comment on the human-queue issue when any of these happens:

1. **Implementer usage limit.** Codex reports a usage or rate limit (for
   example "usage limit", "rate limit" or "try again at" in
   `herdr agent read`), or stalls twice in a row. The lead doesn't take over
   the implementation.
2. **Lead usage limit.** Claude is stopped by its own limit. There's
   nothing to do then; the per-phase checkpoint makes resuming safe.
3. **Commit, push or PR failure.** The implementer cannot commit, push or
   open the PR. Record it on the human-queue issue; the lead does not take
   over.
4. **Blocked.** The next group can't proceed without the human, a
   follow-up round limit was hit (step 5 of the loop), or a PR still cannot
   be merged after the merge bar and review-thread requirements are met.
5. **Done.** Every roadmap box is ticked or carries an `EVIDENCE-HOLD`
   marker.

**To resume after a limit resets,** start the lead again and paste the
kickoff prompt. The run continues from the checkpoint.
