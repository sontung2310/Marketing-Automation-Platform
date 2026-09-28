# Tasks

## 1. 3.1 Vendored catalogue and integrity

- [ ] 1.1 Confirm the upstream `coreyhaines31/marketingskills` license permits vendoring into a client product (stop for a human decision if not). Select and record one upstream commit, confirm all 12 skill names in `docs/agents-spec.md §4.1` exist there, preserve license/notice files, and define the lockfile schema at `backend/app/skills/skills.lock.json`. Measure skill and reference sizes to confirm the load budget of three and the `SKILL_MAX_CHARS` default.
- [ ] 1.2 Vendor the 12 skill directories with their `SKILL.md`, `references/` and `evals/` content; verify every folder has the expected upstream files and no unrelated skill is present.
- [ ] 1.3 Implement `backend/scripts/update_skills.py` with safe pinned-source update and offline `--check` modes, and add `--check` to `npm run check`; verify a clean catalogue passes and a hand-edited or missing/extra file makes `npm run check` exit non-zero with the skill/hash mismatch.
- [ ] 1.4 Add deterministic manifest hashing and lockfile validation tests; verify the same catalogue produces the same per-skill SHA-256 values across runs.

## 2. 3.2 Loader and agent tool

- [ ] 2.1 Add the typed skill metadata, catalogue and loader boundary; verify valid frontmatter produces a folder-matching name and non-empty description, while malformed metadata is rejected before content is returned.
- [ ] 2.2 Implement safe in-directory reference resolution, the `SKILL_MAX_CHARS` cap with a truncation note, and the exact product-context note; verify missing, absolute and traversal references return structured errors and never read outside the selected skill, and oversized content is truncated.
- [ ] 2.3 Add the per-run skill-load session/budget (successful loads only) and typed success/error envelopes; verify the call after three successful loads returns `LIMIT_REACHED` without opening another file, rejected calls do not consume the budget, and no tool path raises into the agent.
- [ ] 2.4 Add Strategy and Execution allowlists, the instruction-catalogue renderer and a typed `load_skill` tool factory; verify each rendered catalogue lists exactly its allowlist and `load_skill("pricing")` is rejected for Execution.
- [ ] 2.5 Add unit/contract coverage for catalogue completeness, reference safety, truncation, allowlist isolation, budget exhaustion and the product-context note; verify scenarios 3-A, 3-B and 3-C with no LLM or database.

## 3. Documentation, layering and quality gates

- [ ] 3.1 Run the affected import-linter/static checks and verify `app.skills` has no MongoDB, MCP, connector or arbitrary-write dependency and reads only the committed catalogue at runtime.
- [ ] 3.2 Update `docs/agents-spec.md §1 and §4` (drop `list_skills`, catalogue in instructions, successful-load budget, character cap, lockfile path), `docs/specs.md` if capability wording changes, and `docs/roadmap.md` (3.1 lockfile path, 3.2 tool list, checked 3.1/3.2 boxes); verify the docs match the implemented contracts.
- [ ] 3.3 Run the affected agent/skill evaluation suite and paste its report in the PR; if the Strategy/Execution suites are still unavailable before Steps 4–5, record evaluation-spec §6 as N/A with that reason and attach the deterministic loader/tool evidence.
- [ ] 3.4 Run `npm run check` and `npm run test:integration` separately; verify both are green and attach the 3-A–3-D test names/pass lines to the PR.
