# Issue tracker: GitHub

Issues for this repo live in GitHub Issues (`sontung2310/Marketing-Automation-Platform`).
Use the `gh` CLI; it infers the repo from `git remote -v`.

| Operation | Command |
|---|---|
| Create | `gh issue create --title "..." --label ready-for-agent --body-file <file>` (use a heredoc or file for multi-line bodies) |
| Read | `gh issue view <number> --comments` |
| List | `gh issue list --state open --json number,title,labels` (add `--label` / `--state` filters) |
| Comment | `gh issue comment <number> --body "..."` |
| Label | `gh issue edit <number> --add-label "..."` / `--remove-label "..."` |
| Close | `gh issue close <number> --comment "..."` |

- **"Publish to the issue tracker"** means create a GitHub issue. **"Fetch the relevant ticket"** means `gh issue view <number> --comments`.
- **Label:** new tickets from `to-tickets` get `ready-for-agent`. Create it once if it's missing: `gh label create ready-for-agent --description "Specified and ready for engineering"`.
- **Blocking edges:** use GitHub's native issue dependencies:
  `gh api --method POST repos/<owner>/<repo>/issues/<blocked>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` comes from `gh api repos/<owner>/<repo>/issues/<n> --jq .id`. If that fails, put `Blocked by: #<n>` at the top of the body.
- **Roadmap link:** every ticket body names its roadmap sub-step (`Roadmap: X.Y`), which the OpenSpec change later repeats.
- **PRs** close their issue with `Closes #<n>` in the PR body.
