// Detect OpenSpec conflicts that `openspec validate` does not catch, across active changes
// (openspec/changes/*, archive excluded):
//
// 1. Cross-change conflicts: two active changes touch the same requirement of one capability.
//    Whichever is archived second would silently overwrite the first.
// 2. Stale base: a delta MODIFIES/REMOVES/RENAMES a requirement missing from the main spec,
//    or ADDS one that already exists there.
// 3. Roadmap link: proposal.md names an existing docs/roadmap.md sub-step ("Roadmap: 4.2").
//
// The patterns below parse OpenSpec's fixed header grammar, not free text
// (docs/coding-conventions.md §4). Usage: node tools/openspec-conflicts.mjs [root]

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SECTION = /^##\s+(ADDED|MODIFIED|REMOVED|RENAMED)\s+Requirements\s*$/i;
const REQUIREMENT = /^###\s+Requirement:\s*(.+?)\s*$/;
const RENAME = /^\s*-\s*(FROM|TO):\s*`?###\s+Requirement:\s*(.+?)`?\s*$/i;
const ROADMAP_ITEM = /^\s*-\s*\[[ xX]\]\s*(\d+\.\d+)\b/gm;
const PROPOSAL_ROADMAP = /roadmap[^\n]*?\b(\d+\.\d+)\b/i;

const normalize = (name) => name.split(/\s+/).join(" ").toLowerCase();
const read = (path) => (existsSync(path) ? readFileSync(path, "utf8") : "");

export function parseDelta(text) {
  const delta = { ADDED: new Set(), MODIFIED: new Set(), REMOVED: new Set(), RENAMED: new Map() };
  let section = null;
  let pendingFrom = null;

  for (const line of text.split("\n")) {
    const sectionMatch = line.match(SECTION);
    if (sectionMatch) {
      section = sectionMatch[1].toUpperCase();
      continue;
    }
    if (line.startsWith("## ")) {
      section = null;
      continue;
    }
    if (section === "RENAMED") {
      const rename = line.match(RENAME);
      if (!rename) continue;
      const name = normalize(rename[2]);
      if (rename[1].toUpperCase() === "FROM") pendingFrom = name;
      else if (pendingFrom) {
        delta.RENAMED.set(pendingFrom, name);
        pendingFrom = null;
      }
      continue;
    }
    const requirement = section && line.match(REQUIREMENT);
    if (requirement) delta[section].add(normalize(requirement[1]));
  }
  return delta;
}

const requirementsIn = (text) =>
  new Set(
    text
      .split("\n")
      .map((line) => line.match(REQUIREMENT))
      .filter(Boolean)
      .map((match) => normalize(match[1])),
  );

const directories = (path) =>
  existsSync(path)
    ? readdirSync(path, { withFileTypes: true }).filter((entry) => entry.isDirectory())
    : [];

export function activeChanges(root) {
  return directories(join(root, "openspec", "changes"))
    .map((entry) => entry.name)
    .filter((name) => name !== "archive")
    .sort();
}

export function check(root) {
  const errors = [];
  const warnings = [];
  const roadmapIds = new Set(
    [...read(join(root, "docs", "roadmap.md")).matchAll(ROADMAP_ITEM)].map((m) => m[1]),
  );
  const touches = new Map(); // "capability/requirement" -> [{ change, op }]
  const claimedSteps = new Map(); // roadmap id -> [change]
  const touch = (key, change, op) => touches.set(key, [...(touches.get(key) ?? []), { change, op }]);

  for (const change of activeChanges(root)) {
    const changeDir = join(root, "openspec", "changes", change);
    const proposal = read(join(changeDir, "proposal.md"));
    if (proposal) {
      const step = proposal.match(PROPOSAL_ROADMAP)?.[1];
      if (!step) {
        errors.push(`${change}: proposal.md must reference a roadmap sub-step, e.g. "Roadmap: 4.2"`);
      } else if (roadmapIds.size && !roadmapIds.has(step)) {
        errors.push(`${change}: roadmap sub-step ${step} does not exist in docs/roadmap.md`);
      } else {
        claimedSteps.set(step, [...(claimedSteps.get(step) ?? []), change]);
      }
    }

    for (const capability of directories(join(changeDir, "specs")).map((entry) => entry.name)) {
      const delta = parseDelta(read(join(changeDir, "specs", capability, "spec.md")));
      const base = requirementsIn(read(join(root, "openspec", "specs", capability, "spec.md")));
      const existing = [...delta.MODIFIED, ...delta.REMOVED, ...delta.RENAMED.keys()];

      for (const name of existing.filter((n) => !base.has(n)).sort()) {
        errors.push(
          `${change}: ${capability}/'${name}' is modified/removed/renamed but does not exist ` +
            "in the main spec (stale base — rebase the change)",
        );
      }
      for (const name of [...delta.ADDED].filter((n) => base.has(n)).sort()) {
        errors.push(`${change}: ${capability}/'${name}' is ADDED but already exists (use MODIFIED)`);
      }

      for (const op of ["ADDED", "MODIFIED", "REMOVED"]) {
        for (const name of delta[op]) touch(`${capability}/'${name}'`, change, op);
      }
      for (const [from, to] of delta.RENAMED) {
        touch(`${capability}/'${from}'`, change, "RENAMED FROM");
        touch(`${capability}/'${to}'`, change, "RENAMED TO");
      }
    }
  }

  for (const [key, ops] of [...touches].sort(([a], [b]) => a.localeCompare(b))) {
    if (new Set(ops.map(({ change }) => change)).size > 1) {
      const detail = ops.map(({ change, op }) => `${change} (${op})`).join(", ");
      errors.push(`conflict: ${key} is changed by multiple active changes: ${detail}`);
    }
  }
  for (const [step, changes] of claimedSteps) {
    if (changes.length > 1) {
      warnings.push(`roadmap sub-step ${step} is claimed by multiple changes: ${changes.join(", ")}`);
    }
  }
  return { errors, warnings };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = resolve(process.argv[2] ?? ".");
  const { errors, warnings } = check(root);
  for (const warning of warnings) console.log(`::warning::${warning}`);
  for (const error of errors) console.log(`::error::${error}`);
  console.log(
    `OpenSpec conflict check: ${activeChanges(root).length} active change(s), ${errors.length} error(s).`,
  );
  process.exitCode = errors.length ? 1 : 0;
}
