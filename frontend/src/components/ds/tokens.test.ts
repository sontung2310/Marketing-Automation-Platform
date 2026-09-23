import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// ui-spec §8: colours, spacing, radius, shadow and type come only from the
// tokens in theme.css. These two rules make that mechanical rather than a
// matter of review.
const DS_DIR = dirname(fileURLToPath(import.meta.url));
const SOURCES = readdirSync(DS_DIR).filter(
  (file) => file.endsWith(".tsx") && !file.endsWith(".test.tsx"),
);

describe("design-system primitives", () => {
  it("ships at least the primitives the workspace composes from", () => {
    expect(SOURCES.length).toBeGreaterThanOrEqual(12);
  });

  it.each(SOURCES)("%s uses no inline style attribute", (file) => {
    expect(readFileSync(join(DS_DIR, file), "utf8")).not.toMatch(/\sstyle=\{/);
  });

  it.each(SOURCES)("%s uses no arbitrary Tailwind value", (file) => {
    const source = readFileSync(join(DS_DIR, file), "utf8");
    for (const [, classes] of source.matchAll(/className=(?:"([^"]*)"|\{[^}]*\})/g)) {
      expect(classes ?? "").not.toMatch(/[a-z-]\[/);
    }
  });
});
