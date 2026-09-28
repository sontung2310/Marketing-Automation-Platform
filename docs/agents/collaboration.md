# Way of working

> Pointer: AGENTS.md §3–§4. Read this before starting or resuming a Step.

The same agent plans and implements a Step. A fresh reviewer subagent judges
the PR, and a human approves and merges outside autopilot.

## Per Step

1. **Pick.** Take the next unchecked Step in `docs/roadmap.md` without an
   `EVIDENCE-HOLD` marker, unless a Step is already in flight (an open
   `feature/*` branch or PR). An `EVIDENCE-HOLD` sub-step is resumed when its
   evidence can be produced: remove the marker and tick its box once the
   evidence meets AGENTS.md §5. A defect in an already-merged Step gets its own
   GitHub issue ([issue-tracker.md](issue-tracker.md)) and a commit on the
   current Step branch, unless it breaks `main` and needs its own PR.
2. **Specify.** For system-behaviour work, run `openspec-propose` for the
   Step. The change lists every `Roadmap: X.Y` sub-step and every
   Given/When/Then scenario in the Step's success-criteria table; it replaces
   a Step issue. Validate it with `npm run openspec:check`. Outside autopilot,
   the human approves the change once before implementation. In autopilot,
   the human reviews the delta specs in the Step PR instead.
   - **Discovery or doc-only Steps** (e.g. verifying the data contract against
     the live cluster) have no OpenSpec change; the roadmap sub-steps are the
     scope. Don't invent a change to satisfy the workflow table.
3. **Implement.** On branch `feature/<step-number>-<slug>`, work the
   sub-steps in roadmap order with `openspec-apply-change`, checking tasks off
   in `tasks.md`. After each sub-step, run `npm run check` and the
   success-criteria scenarios scoped to it against a real environment, then
   commit (Conventional Commits) and push before starting the next.
4. **PR.** When every sub-step is verified, open one PR from
   `.github/pull_request_template.md`. It lists every `Roadmap: X.Y`
   sub-step, the OpenSpec change (or `none`), evidence for every Step
   success-criteria scenario, and ticks the Step's roadmap boxes so the ticks
   land on `main` with the merge. In autopilot, add the `autopilot` label.
5. **Review.** Spawn the fair reviewer (below). Fix each finding in another
   commit, or answer it on the PR with a written reason. Then archive the
   OpenSpec change with `openspec-archive-change` and push.
6. **Merge.** Only under the AGENTS.md §4 merge bar: the human outside
   autopilot, `gh pr merge --squash` in autopilot. Resolve each review thread
   after its finding is fixed or answered:

   ```bash
   gh api graphql -f query='mutation($threadId:ID!) { resolveReviewThread(input:{threadId:$threadId}) { thread { isResolved } } }' -F threadId=<thread-id>
   ```

   After merging, sync `main` locally.

If a sub-step still fails after 3 fix attempts, stop: outside autopilot ask
the human; in autopilot record it on the human queue.

## Fair review

The reviewer judges the PR against the spec and the standards, not against
the author's intentions.

- **Fresh, minimal context.** Spawn the reviewer with the Agent tool and pass
  only the prompt below — never the conversation or an opinion of the work.
- **Same prompt every time.** Only the placeholders change:

  ```text
  Review PR #<n> (branch <branch>) against origin/main.
  OpenSpec change: `openspec/changes/<change>/` or `none` (discovery or doc-only work).
  Roadmap sub-steps: <X.Y, ...> in docs/roadmap.md.
  Run independent passes in separate sub-agents:
  1. Spec: does the diff implement the Step's success-criteria scenarios and the
     delta specs, no more and no less?
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
  finding next to its answer.

## Autopilot

Autopilot runs "Per Step" Step after Step through `docs/roadmap.md`, without
a human in the chat, until a stop condition is met.

### Rules

**Specify just-in-time, one Step at a time.** A later Step's OpenSpec change
is not written in advance, because what an earlier Step discovers changes
what it should say.

**Grill only genuinely open behaviour.** The roadmap's success criteria are
already Given / When / Then, so the OpenSpec change is written straight from
them. `grill-me` is for a decision the specs haven't made.

**When something is open, decide — don't stop.** Pick the default most
consistent with the existing specs, record the decision in the PR, and add a
comment to the human queue. Each entry names the decision, the rejected
alternative, the spec that made it the most consistent default, where it
landed, and how reversible it is. Silence from a human means accepted; a
reply gets folded back into the spec or the relevant doc.

**Stop only when the decision is architectural or irreversible:** the layering
in AGENTS.md §2, a data contract that later Steps would have to be rebuilt
around, anything that writes to a source system, and anything that costs money
or is publicly visible.

**Check the data environment first.** Before work that touches a data
source, confirm the MongoDB MCP runs with `--readOnly` and targets the same
cluster as this repo's `.env`. If not, record it on the human queue and stop.

**Labels.** `autopilot` — worked by the loop without per-step human approval.
`needs-human` — carries a decision for the human on duty.

### Human queue

Human-only items go into one standing GitHub issue titled **"Autopilot:
waiting on a human"**
([#4](https://github.com/sontung2310/Marketing-Automation-Platform/issues/4),
labels `needs-human` and `autopilot`), one comment per item. Adding an item
doesn't stop the run. Queue items include:

- decisions the spec leaves open (also recorded in the PR);
- judge calibration (evaluation-spec §5.2) — the baseline is provisional
  until it's done;
- the demo dry-run with an outsider (8-E);
- anything that needs a credential, money or an account.

### Checkpoint and resume

A run can hit a usage limit mid-sentence, so progress is saved after every
phase.

- **Ground truth:** the checkboxes and `EVIDENCE-HOLD` markers in
  `docs/roadmap.md` on `main` (marker semantics in its header), plus open PRs
  with the `autopilot` label.
- **Checkpoint:** `.handoffs/autopilot.md` (gitignored), rewritten after every
  phase change. It records the Step and sub-step in progress with its branch
  and PR, the phase (`SPECIFY`, `IMPLEMENT`, `VERIFY`, `PR`, `REVIEW` or
  `MERGE`) and the fix-attempt count.
- **Resume:** read the checkpoint, reconcile it against the ground truth (a
  merged PR means that Step is done; when they disagree, trust GitHub), and
  finish work in flight before starting anything new.

### Stop conditions

Stop, rewrite the checkpoint with the reason, and post a summary on the
human-queue issue when:

1. **Usage limit.** The run is stopped by its own limit; the checkpoint makes
   resuming safe.
2. **Blocked.** The next Step can't proceed without the human, the fix-attempt
   limit was hit, or a PR cannot meet the merge bar.
3. **Done.** Every roadmap box is ticked or carries an `EVIDENCE-HOLD` marker.

To resume, start a new session and ask it to continue autopilot; it resumes
from the checkpoint.
