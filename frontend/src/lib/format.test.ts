import { describe, expect, it } from "vitest";

import { compactNumber, displayUrl, initials, money, relativeTime, signedPercent } from "./format";

const NOW = new Date("2026-09-23T12:00:00Z").getTime();

describe("relativeTime", () => {
  it.each([
    ["2026-09-23T11:58:00Z", "2 min ago"],
    ["2026-09-23T09:00:00Z", "3h ago"],
    ["2026-09-19T12:00:00Z", "4d ago"],
    ["2026-09-23T11:59:59Z", "just now"],
  ])("renders %s as %s", (iso, expected) => {
    expect(relativeTime(iso, NOW)).toBe(expected);
  });
});

describe("signedPercent", () => {
  it("carries direction in the arrow as well as the sign", () => {
    expect(signedPercent(142)).toBe("▲142%");
    expect(signedPercent(-12.34)).toBe("▼12.3%");
    expect(signedPercent(0)).toBe("0%");
  });
});

describe("compactNumber", () => {
  it("keeps ranking differences visible", () => {
    expect(compactNumber(999)).toBe("999");
    expect(compactNumber(48200)).toBe("48.2K");
    expect(compactNumber(1_200_000)).toBe("1.2M");
  });
});

describe("money", () => {
  it("renders concrete, grouped amounts", () => {
    expect(money(2500, "AUD")).toBe("$2,500");
  });
});

describe("initials", () => {
  it("takes at most two initials", () => {
    expect(initials("Aisha Patel")).toBe("AP");
    expect(initials("Kestrel Growth Co.")).toBe("KG");
  });
});

describe("displayUrl", () => {
  it("strips the scheme and clips long paths", () => {
    expect(displayUrl("https://www.brightlane.example/pricing")).toBe("brightlane.example/pricing");
    expect(displayUrl("https://brightlane.example/blog/a-very-long-article-slug")).toMatch(/…$/);
  });
});
