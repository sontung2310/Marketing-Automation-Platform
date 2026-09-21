# Lead / implementer collaboration (Herdr)

> Pointer: AGENTS.md §4. Read this before starting or resuming a loop, in any
> role.

| Role | Agent | Owns |
|---|---|---|
| **Lead** | Claude Code, Opus 5 at the highest effort | The issue end to end: writes the OpenSpec change, briefs the implementer, verifies every result itself, decides when the work is done, spawns the reviewer. Leaves implementation files alone while the implementer works. |
| **Implementer** | Codex, `gpt-5.6-terra` at `xhigh` (`~/.codex/config.toml`) | Exactly the briefed tasks, via `openspec-apply-change`: implements, checks, reports. Commits and opens the PR when the lead says so. |
| **Reviewer** | A fresh Claude subagent, spawned by the lead | An independent verdict on the PR (see "Fair review") |
| **Human** | The engineer on duty | Approving the OpenSpec change, answering escalations, merging. In **autopilot**, the lead self-approves and merges, and the human audits asynchronously through the human queue (see "Autopilot"). |

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
   - **Context:** the issue, the OpenSpec change path and `Roadmap: X.Y`.
   - **Scope:** exact task IDs from `tasks.md`.
   - **Constraints:** AGENTS.md, `docs/coding-conventions.md`, and files to
     leave untouched.
   - **Done when:** checks to run, success-criteria scenarios to prove.
   - **Report format:** as in step 3.
2. **Implement.** The implementer works the tasks and checks them off in
   `tasks.md`.
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
   with `tasks.md` and the delta specs.
5. **Follow up.** Each follow-up names the file and line, the failing output
   and the expected behaviour. Allow at most **3 rounds per task group**;
   after that, escalate to the human with a summary.
6. **Finish.** When verification is green, the lead tells the implementer to
   do the following:
   - archive the OpenSpec change;
   - tick the roadmap box;
   - commit with a Conventional Commit message;
   - push `feature/<step-number>-<slug>`;
   - open the PR from `.github/pull_request_template.md`, with the roadmap
     sub-step(s) and `Closes #<issue>` in the body.
7. **Review.** The lead spawns the reviewer. Every finding is either fixed
   through another loop round, or answered on the PR with a written reason.
8. **Merge.** The human merges when CI is green and every finding has an
   answer.

**Blocked or stalled implementer.** On `blocked` (an approval or question
UI), the lead reads the pane and puts the question to the human. On
`timeout` or `agent_prompt_stalled`, the lead reads the pane before
re-sending, because the prompt may already have arrived.

## Fair review

The reviewer judges the PR against the spec and the standards. It doesn't
judge it against the lead's intentions or the implementer's self-assessment.

- **Fresh, minimal context.** The lead spawns the reviewer with the Agent
  tool and passes only the prompt below. It never includes its own
  conversation, the implementer's reports, or an opinion of the work.
- **Same prompt every time.** Only the three placeholders change:

  ```text
  Review PR #<n> (branch <branch>) against origin/main. Linked issue: #<issue>.
  OpenSpec change: openspec/changes/<change>/.
  Run two independent passes in separate sub-agents:
  1. Spec: does the diff implement the issue's acceptance criteria and the delta
     specs, no more and no less?
  2. Standards: does it follow AGENTS.md and docs/coding-conventions.md (§11 checklist),
     including security, error handling and tests?
  Report each finding as: file:line · severity (high/medium/low) · concrete failure
  scenario. Verify every finding by tracing or reproducing it before reporting.
  Report "no findings" for a pass with none. Post the result as a PR review.
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

**An OpenSpec change is only required when system behaviour changes.** A
sub-step that is pure investigation or documentation — inspecting source
collections, rewriting a contract doc — still goes through everything else:
a GitHub issue, a `feature/<step-number>-<slug>` branch, a PR naming its
roadmap sub-step(s), the fair review, and a green **Check**. It just has no
`openspec/changes/<name>/`, and the PR says so instead of naming one. Don't
invent a change to satisfy the workflow table.

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
that touches a data source, confirm its MongoDB MCP runs with `--readOnly`
(`~/.codex/config.toml` → `[mcp_servers.mongodb]`) and that it points at the
same cluster as this repo's `.env`. If either is wrong, stop and tell the
human.

**Labels.** `ready-for-agent` — specified, engineering can pick it up.
`autopilot` — being worked by the loop without per-step human approval.
`needs-human` — carries a decision for the human on duty.

### Checkpoint and resume

Claude can hit its own usage limit mid-sentence, so progress is saved after
every phase, never only at the end.

- **Ground truth:** the checkboxes in `docs/roadmap.md` on `main` (merged
  work), plus open GitHub issues and PRs with the `autopilot` label (work in
  flight).
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

1. **Pick.** Take the next unchecked sub-steps in roadmap order, grouped
   only when they're tightly related (usually 1–3; never across Steps).
   Done when the group and its slug are in the checkpoint.
2. **Issue.** Create one GitHub issue using
   [issue-tracker.md](issue-tracker.md) and the `to-tickets` issue template,
   without the interactive quiz. Labels: `ready-for-agent` and `autopilot`
   (create any missing label once with `gh label create`).
   The issue carries the sub-steps' Given/When/Then success criteria from
   the roadmap as its acceptance criteria. Done when the issue exists.
3. **Specify.** The lead runs `openspec-propose` for the issue
   (`Roadmap: X.Y`), validates it with `npm run openspec:check`, and
   self-approves. The human reviews the delta specs in the PR instead. Done
   when validation passes.
   - **Discovery or doc-only sub-steps** (e.g. 0.3–0.4, verifying the data
     contract against the live cluster) change no system behaviour, so they
     get **no OpenSpec change** — skip straight to step 4. They are still
     briefed to the implementer like any other work: Codex has its own
     MongoDB MCP, and the lead verifies the result by spot-checking the
     source itself rather than by doing the inspection for it.
4. **Brief → implement → report → verify → follow up.** Run the loop above
   on branch `feature/<step-number>-<slug>`, starting a fresh implementer
   conversation for each group (Codex's `/new`). Done when the lead's own
   verification is green: `npm run check`, plus every success-criteria
   scenario of the group run against a real environment.
5. **PR.** Codex commits, pushes and opens the PR with `Roadmap: …`,
   `Closes #<issue>` and the `autopilot` label. If its sandbox blocks the
   push, the lead runs the same git and `gh` commands. Done when the
   **Check** job is green on the PR.
6. **Review.** Spawn the fair reviewer. Fix each finding through another
   loop round, or answer it on the PR. Done when every finding has a fix or
   an answer, and no high-severity finding is merely answered.
7. **Merge.** In autopilot the lead squash-merges the PR, then syncs `main`
   locally. The human audits merged work asynchronously, and can revert it.
   Done when `main` contains the ticked roadmap boxes and CI on `main` is
   green.

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
3. **Blocked.** The next group can't proceed without the human, a
   follow-up round limit was hit (step 5 of the loop), or a PR can't be
   merged.
4. **Done.** Every roadmap box is ticked.

**To resume after a limit resets,** start the lead again and paste the
kickoff prompt. The run continues from the checkpoint.
