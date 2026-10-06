import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// ui-spec §8: colours, spacing, radius, shadow and type come only from the
// tokens in theme.css. These rules make that mechanical rather than a matter
// of review, for every component, not just the primitives: a stray literal
// colour would also silently break the dark theme.
const DS_DIR = dirname(fileURLToPath(import.meta.url));
const SRC_DIR = join(DS_DIR, "../..");
const isComponent = (file: string) => file.endsWith(".tsx") && !file.endsWith(".test.tsx");
const SOURCES = readdirSync(DS_DIR).filter(isComponent);
const ALL_SOURCES = readdirSync(SRC_DIR, { recursive: true, encoding: "utf8" })
  .filter((file) => isComponent(file) && !file.startsWith("test"))
  .map((file) => relative(DS_DIR, join(SRC_DIR, file)));

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

  it.each(ALL_SOURCES)("%s uses no inline style attribute", (file) => {
    expect(readFileSync(join(DS_DIR, file), "utf8")).not.toMatch(/\sstyle=\{/);
  });

  it.each(ALL_SOURCES)("%s uses no literal colour", (file) => {
    const source = readFileSync(join(DS_DIR, file), "utf8");
    expect(source.match(/#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(/gi) ?? []).toEqual([]);
  });

  it.each(ALL_SOURCES)("%s uses no arbitrary Tailwind value", (file) => {
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
