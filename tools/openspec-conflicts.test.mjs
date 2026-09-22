import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { check, parseDelta } from "./openspec-conflicts.mjs";

const MODIFY = "## MODIFIED Requirements\n### Requirement: Topic recommendations\nnew text\n";
const PROJECT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function write(path, content) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function repo() {
  const root = mkdtempSync(join(tmpdir(), "openspec-conflicts-"));
  write(join(root, "docs/roadmap.md"), "- [ ] 4.1 Run service\n- [ ] 4.2 Strategy agent\n- [x] 0.1 Scaffold\n");
  write(
    join(root, "openspec/specs/strategy-agent/spec.md"),
    "# Strategy\n### Requirement: Topic recommendations\ntext\n",
  );
  mkdirSync(join(root, "openspec/changes/archive"), { recursive: true });
  return root;
}

function change(root, name, delta, proposal = "Roadmap: 4.2\n") {
  write(join(root, "openspec/changes", name, "proposal.md"), proposal);
  write(join(root, "openspec/changes", name, "specs/strategy-agent/spec.md"), delta);
}

test("parseDelta reads every section", () => {
  const delta = parseDelta(
    "## ADDED Requirements\n### Requirement: A\n" +
      "## MODIFIED Requirements\n### Requirement: B\n" +
      "## REMOVED Requirements\n### Requirement: C\n" +
      "## RENAMED Requirements\n- FROM: `### Requirement: D`\n- TO: `### Requirement: E`\n",
  );
  assert.deepEqual([...delta.ADDED], ["a"]);
  assert.deepEqual([...delta.MODIFIED], ["b"]);
  assert.deepEqual([...delta.REMOVED], ["c"]);
  assert.deepEqual([...delta.RENAMED], [["d", "e"]]);
});

test("a single valid change passes", () => {
  const root = repo();
  change(root, "strategy-topics", MODIFY);
  assert.deepEqual(check(root), { errors: [], warnings: [] });
});

test("an end-of-line evidence hold preserves its roadmap id", () => {
  const root = repo();
  write(join(root, "docs/roadmap.md"), readFileSync(join(PROJECT_ROOT, "docs/roadmap.md"), "utf8"));
  change(root, "evidence-hold", MODIFY, "Roadmap: 0.1\n");
  assert.deepEqual(check(root), { errors: [], warnings: [] });
});

test("two changes modifying the same requirement conflict", () => {
  const root = repo();
  change(root, "change-a", MODIFY);
  change(root, "change-b", MODIFY, "Roadmap: 4.1\n");
  const { errors } = check(root);
  assert.equal(errors.length, 1);
  assert.match(errors[0], /conflict.*change-a.*change-b/);
});

test("an added name colliding with a rename target conflicts", () => {
  const root = repo();
  change(root, "adds", "## ADDED Requirements\n### Requirement: Response plans\n");
  change(
    root,
    "renames",
    "## RENAMED Requirements\n- FROM: `### Requirement: Topic recommendations`\n" +
      "- TO: `### Requirement: Response plans`\n",
    "Roadmap: 4.1\n",
  );
  assert.ok(check(root).errors.some((e) => e.includes("conflict") && e.includes("response plans")));
});

test("stale base and duplicate add are errors", () => {
  const root = repo();
  change(
    root,
    "stale",
    "## MODIFIED Requirements\n### Requirement: Does not exist\n" +
      "## ADDED Requirements\n### Requirement: Topic recommendations\n",
  );
  const { errors } = check(root);
  assert.ok(errors.some((e) => e.includes("stale base")));
  assert.ok(errors.some((e) => e.includes("already exists")));
});

test("a proposal must reference an existing roadmap sub-step", () => {
  const missing = repo();
  change(missing, "no-ref", MODIFY, "Just a proposal\n");
  assert.ok(check(missing).errors.some((e) => e.includes("must reference a roadmap sub-step")));

  const unknown = repo();
  change(unknown, "unknown", MODIFY, "Roadmap: 9.9\n");
  assert.ok(check(unknown).errors.some((e) => e.includes("9.9 does not exist")));
});

test("two changes claiming one roadmap sub-step warn but pass", () => {
  const root = repo();
  change(root, "one", "## ADDED Requirements\n### Requirement: X\n");
  change(root, "two", "## ADDED Requirements\n### Requirement: Y\n");
  const { errors, warnings } = check(root);
  assert.deepEqual(errors, []);
  assert.ok(warnings.some((w) => w.includes("4.2 is claimed by multiple changes")));
});
