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
  it("ships every primitive the workspace composes from", () => {
    expect([...SOURCES].sort()).toEqual([
      "Badge.tsx",
      "Button.tsx",
      "EmptyState.tsx",
      "ErrorState.tsx",
      "Icon.tsx",
      "LiveRegion.tsx",
      "Menu.tsx",
      "Panel.tsx",
      "SegmentedSwitcher.tsx",
      "Sheet.tsx",
      "Skeleton.tsx",
      "Spinner.tsx",
      "Tabs.tsx",
      "TextInput.tsx",
    ]);
  });

  it.each(SOURCES)("%s uses no inline style attribute", (file) => {
    expect(readFileSync(join(DS_DIR, file), "utf8")).not.toMatch(/\sstyle=\{/);
  });

  it.each(SOURCES)("%s uses no arbitrary Tailwind value", (file) => {
    const source = readFileSync(join(DS_DIR, file), "utf8");

    // Every double-quoted string, not just a literal className attribute: the
    // variants these primitives are built from live in Record constants and in
    // cn() calls, which an attribute-only match silently skipped.
    const offenders = [...source.matchAll(/"([^"\n]*)"/g)]
      .map(([, value]) => value ?? "")
      .filter((value) => /[a-z-]\[/.test(value));

    expect(offenders).toEqual([]);
  });
});
