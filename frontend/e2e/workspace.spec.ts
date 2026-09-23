import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/** A clean visit: no restored session, so the transcript starts empty. */
async function openWorkspace(page: Page): Promise<string[]> {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));

  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await expect(page.getByRole("region", { name: "Social listening" })).toBeVisible();
  return consoleErrors;
}

test.describe("7-A the workspace loads at the design target", () => {
  test("renders every region, the tenant, the keywords and the last sync", async ({ page }) => {
    const consoleErrors = await openWorkspace(page);

    await expect(page.getByRole("region", { name: "Social listening" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Execution agent" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Strategy recommendations" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Competitor activity" })).toBeVisible();

    await expect(page.getByRole("button", { name: "Choose the tenant" })).toHaveText(
      /Marketing Eye/,
    );
    await expect(page.getByText(/^Last sync /)).toBeVisible();
    for (const keyword of [
      "AI search",
      "content strategy",
      "B2B growth",
      "brand clarity",
      "demand generation",
    ]) {
      await expect(page.getByRole("listitem").filter({ hasText: keyword })).toBeVisible();
    }

    await expect(
      page.getByText("Pick an item from the feed, or ask Execution for a deliverable."),
    ).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });

  test("passes an axe accessibility scan with no violations", async ({ page }) => {
    await openWorkspace(page);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(results.violations.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
  });
});

test.describe("7-C an Execution run streams into the transcript", () => {
  test("shows the trigger, the thinking line, progress, the answer and the deliverable", async ({
    page,
  }) => {
    await openWorkspace(page);

    const feed = page.getByRole("region", { name: "Competitor activity" });
    const blogCard = feed.getByRole("article").filter({ hasText: "NEW_BLOG" }).first();
    await blogCard.scrollIntoViewIfNeeded();

    const transcript = page.getByLabel("Execution transcript");
    // Sample the transcript while the run streams: it must never sit
    // unchanged for 10 seconds (docs/specs.md §8).
    const samples: { at: number; text: string }[] = [];
    const started = Date.now();
    await blogCard.getByRole("button", { name: "Create a similar blog" }).click();

    while (Date.now() - started < 6000) {
      samples.push({ at: Date.now() - started, text: await transcript.innerText() });
      await page.waitForTimeout(400);
    }

    let lastChangeAt = 0;
    let longestGap = 0;
    let previous = samples[0]?.text ?? "";
    for (const sample of samples) {
      if (sample.text === previous) continue;
      longestGap = Math.max(longestGap, sample.at - lastChangeAt);
      lastChangeAt = sample.at;
      previous = sample.text;
    }
    longestGap = Math.max(longestGap, (samples.at(-1)?.at ?? 0) - lastChangeAt);
    expect(longestGap).toBeLessThan(10_000);

    await expect(transcript.getByText("CREATE_SIMILAR · BLOG_DRAFT")).toBeVisible();

    const thinking = transcript
      .getByRole("button", { name: /Thought for \d+s, used \d+ tools/ })
      .last();
    await expect(thinking).toBeVisible();
    await expect(transcript.getByText(/Drafted in first person/).last()).toBeVisible();
    await expect(transcript.getByText("CEO_POST · LINKEDIN · 218 words").last()).toBeVisible();

    // Expanding the collapsed line reveals the reasoning steps and one row per tool.
    await thinking.click();
    await expect(transcript.getByText("Loading company context").last()).toBeVisible();
    await expect(transcript.getByText("search_competitor_activity").last()).toBeVisible();

    // Only the marketer's own messages use a bubble.
    await page.getByLabel("Message the Execution agent").fill("Make it shorter");
    await page.getByRole("button", { name: "Send" }).click();
    const bubble = transcript.getByText("Make it shorter");
    await expect(bubble).toBeVisible();
    await expect(bubble).toHaveClass(/rounded-lg/);
    // Agent output is structured blocks, never a bubble (ui-spec §8).
    await expect(transcript.getByText(/Drafted in first person/).last()).not.toHaveClass(
      /rounded-lg/,
    );
  });
});

test.describe("7-D the evidence loop", () => {
  test("Do this prefills the composer without sending, and evidence scrolls to its target", async ({
    page,
  }) => {
    await openWorkspace(page);

    let runsCreated = 0;
    await page.route("**/api/runs", async (route) => {
      runsCreated += 1;
      await route.continue();
    });

    await page.getByRole("button", { name: /Hold price, publish the reasoning/ }).click();

    const sheet = page.getByRole("dialog", { name: "Recommendation 1" });
    await expect(sheet).toBeVisible();
    await expect(sheet).toHaveCSS("width", "440px");
    await expect(sheet.getByText("Hold price, publish the reasoning")).toBeVisible();
    await expect(
      sheet.getByText(/Brightlane raised its executive visibility package/),
    ).toBeVisible();

    const chip = sheet.getByRole("button", { name: /Raised its executive visibility package/ });
    await expect(chip).toHaveAttribute("title", "act_seed_028");
    await chip.click();

    const target = page.locator("#evidence-act_seed_028");
    await expect(target).toBeInViewport();
    await expect(target).toHaveClass(/bg-surface-selected/);

    await page.getByRole("button", { name: /Hold price, publish the reasoning/ }).click();
    await page.getByRole("button", { name: "Do this" }).click();

    await expect(page.getByLabel("Message the Execution agent")).toHaveValue(
      "Write the LinkedIn post for recommendation #1",
    );
    expect(runsCreated).toBe(0);
  });
});

test.describe("7-E degraded regions and narrow viewports", () => {
  test("shows a failing region's message verbatim while the rest keep working", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.__fixtureFailures = [
        {
          path: "/api/recommendations",
          status: 503,
          code: "UPSTREAM_UNAVAILABLE",
          message: "Strategy is unavailable: the agent service is down.",
        },
      ];
    });
    await openWorkspace(page);

    const strategy = page.getByRole("region", { name: "Strategy recommendations" });
    await expect(
      strategy.getByText("Strategy is unavailable: the agent service is down."),
    ).toBeVisible();
    await expect(strategy.getByRole("button", { name: "Retry" })).toBeVisible();

    const feed = page.getByRole("region", { name: "Competitor activity" });
    await expect(feed.getByRole("article").first()).toBeVisible();
    await expect(page.getByRole("region", { name: "Social listening" })).toBeVisible();
    await expect(page.getByLabel("Message the Execution agent")).toBeEditable();
  });

  test("collapses to one column with the region switcher and never scrolls sideways", async ({
    page,
  }) => {
    await openWorkspace(page);
    await page.setViewportSize({ width: 900, height: 800 });

    const switcher = page.getByRole("tablist", { name: "Workspace region" });
    await expect(switcher).toBeVisible();
    for (const label of ["Feed", "Workspace", "Insights"]) {
      await expect(switcher.getByRole("tab", { name: label })).toBeVisible();
    }

    await switcher.getByRole("tab", { name: "Feed" }).click();
    await expect(page.getByRole("region", { name: "Competitor activity" })).toBeVisible();

    for (const width of [1440, 1280, 900, 760]) {
      await page.setViewportSize({ width, height: 800 });
      await page.waitForTimeout(150);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(0);
    }
  });
});
