# Design

## Context

See `proposal.md` for motivation. The repository currently has an empty
`backend/app/skills/library/` and package shells for the two agents. The
authoritative skill list, per-agent allowlists and product-context rule are in
`docs/agents-spec.md §4.1–4.2`; the import-linter already treats
`app.skills` as a read-only layer. The implementation must remain compatible
with the later Strategy and Execution `RunContext` without building those
agents in this Step.

## Goals / Non-Goals

**Goals:**

- Make the committed catalogue reproducible and tamper-evident.
- Parse skill metadata and references once at the boundary into typed values.
- Provide small, reusable tool factories that receive an agent allowlist and a
  per-run budget rather than relying on global mutable state.
- Keep runtime skill loading local, read-only and safe from path traversal.

**Non-Goals:**

- Building either agent, router, MCP client, eval harness or golden dataset.
- Fetching or refreshing upstream content during an agent run.
- Interpreting skill prose, executing code from a skill, or adding database
  access.

## Decisions

1. **Commit and hash the catalogue.** The maintenance CLI fetches a selected
   upstream commit, copies the exact 12 directories, and writes a lockfile
   containing the commit, source URL and a SHA-256 manifest for each skill.
   `--check` is offline and compares every tracked file, while an update mode
   is the only path allowed to contact GitHub. Runtime fetching was rejected:
   it would make agent output depend on network state and unreviewed content.

2. **Use a real YAML parser at the boundary.** `SKILL.md` frontmatter is
   parsed with the existing PyYAML dependency (made explicit if needed), then
   validated into a small Pydantic model requiring `name` and `description`.
   Splitting strings or using regex was rejected because malformed YAML and
   nested metadata would be silently accepted.

3. **Separate catalogue, session budget and tool wrappers.** A catalogue owns
   immutable parsed skills; a per-run session owns the three-call counter; and
   typed tool factories bind the current agent's allowlist to those objects.
   A module-level counter was rejected because concurrent agent runs would
   share state. The session interface is intentionally small so Step 4 can
   attach it to `RunContext` without changing tool contracts.

4. **Resolve references under the selected skill root.** The loader resolves
   a requested reference, rejects absolute paths, `..` traversal and symlinks
   outside the skill directory, and then reads one file. Allowing arbitrary
   repository paths was rejected because vendored text is untrusted input.

5. **Return typed recoverable tool results.** Success and error envelopes are
   represented by Pydantic models. The wrapper checks the allowlist before
   exposing content and increments the session budget for every load attempt;
   `LIMIT_REACHED` therefore cannot be bypassed with unknown-name probes.
   Tools return errors to the agent rather than raising.

6. **Preserve upstream attribution.** The vendored tree keeps upstream
   `references/`, `evals/` and license/notice files. The update check fails on
   missing, extra or changed files so reviewers can see exactly what changed.

## Risks / Trade-offs

- **[Upstream layout changes]** → the pinned commit and exact skill manifest
  make updates explicit; the update CLI fails closed when a required skill or
  expected `SKILL.md` is missing.
- **[Large skill bodies increase prompt tokens]** → `list_skills` returns only
  summaries, `load_skill` loads one skill or reference on demand, and the
  existing per-run limit remains three.
- **[Malformed or hostile vendored markdown]** → metadata and paths are
  validated before content is returned; the agent receives text as data and
  never executes it.
- **[No agent eval suite yet]** → the implementation PR records evaluation
  §6 as N/A until Steps 4–5 create the Router, Strategy and Execution suites;
  deterministic loader and allowlist tests remain the gate for this Step.

## Migration Plan

No database or runtime data migration is required. Add the catalogue and
loader behind the existing `app.skills` package, run the integrity check and
unit tests, then wire the resulting tool factories into agents when Steps 4–5
are implemented. Rollback is removing the new skill package and lockfile;
existing MCP and pipeline behavior is unaffected.
