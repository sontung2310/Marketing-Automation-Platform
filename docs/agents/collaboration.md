# Lead / implementer collaboration (Herdr)

> Pointer: AGENTS.md §4. Read this before starting or resuming a loop, in any
> role.

| Role | Agent | Owns |
|---|---|---|
| **Lead** | Claude Code, Opus 5 at the highest effort | The issue end to end: writes the OpenSpec change, briefs the implementer, verifies every result itself, decides when the work is done, spawns the reviewer. Leaves implementation files alone while the implementer works. |
| **Implementer** | Codex, `gpt-5.6-terra` at `xhigh` (`~/.codex/config.toml`) | Exactly the briefed tasks, via `openspec-apply-change`: implements, checks, reports. Commits and opens the PR when the lead says so. |
| **Reviewer** | A fresh Claude subagent, spawned by the lead | An independent verdict on the PR (see "Fair review") |
| **Human** | The engineer on duty | Approving the OpenSpec change, answering escalations, merging |

## Setup

1. Run Claude Code **inside a Herdr pane** (`test "$HERDR_ENV" = 1`). The
   loop can't run from outside Herdr.
2. Start the implementer in a sibling pane:

   ```bash
   herdr pane split --current --direction right --cwd "$PWD" --no-focus   # → .result.pane.pane_id
   herdr agent start implementer --kind codex --pane <pane_id>
   ```

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
   `make check` and the success-criteria scenarios, and compares the result
   with `tasks.md` and the delta specs.
5. **Follow up.** Each follow-up names the file and line, the failing output
   and the expected behaviour. Allow at most **3 rounds per task group**;
   after that, escalate to the human with a summary.
6. **Finish.** When verification is green, the lead tells the implementer to
   do the following:
   - archive the OpenSpec change;
   - tick the roadmap box;
   - commit with a Conventional Commit message;
   - push `feature/<step>-<slug>`;
   - open the PR from `.github/pull_request_template.md`, with
     `Closes #<issue>` in the body.
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
