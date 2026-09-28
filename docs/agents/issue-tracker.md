# Issue tracker: GitHub

Step work is tracked by its OpenSpec change and `docs/roadmap.md`, not by
issues. GitHub Issues (`sontung2310/Marketing-Automation-Platform`) hold only:

- **bugs** found in an already-merged Step;
- the standing **human queue**,
  [#4 "Autopilot: waiting on a human"](https://github.com/sontung2310/Marketing-Automation-Platform/issues/4).

Use the `gh` CLI; it infers the repo from `git remote -v`.

| Operation | Command |
|---|---|
| Create | `gh issue create --title "..." --label bug --body-file <file>` (use a heredoc or file for multi-line bodies) |
| Read | `gh issue view <number> --comments` |
| List | `gh issue list --state open --json number,title,labels` (add `--label` / `--state` filters) |
| Comment | `gh issue comment <number> --body "..."` |
| Label | `gh issue edit <number> --add-label "..."` / `--remove-label "..."` |
| Close | `gh issue close <number> --comment "..."` |

- A bug issue names the broken behaviour, how to reproduce it and the Step it
  came from. The PR that fixes it says `Fixes #<n>`.
