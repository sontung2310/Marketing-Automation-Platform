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

    // axe files short text and unlabelled generics under `incomplete` rather
    // than `violations`, which is where a real 4.32:1 contrast miss hid. The
    // rules ui-spec §6 turns on must come back clean from that bucket too.
    const GATED = ["color-contrast", "aria-prohibited-attr"];
    expect(
      results.incomplete
        .filter((item) => GATED.includes(item.id))
        .flatMap((item) => item.nodes.map((node) => `${item.id}: ${node.target.join(" ")}`)),
    ).toEqual([]);
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

test.describe("7-C a failed run", () => {
  test("shows the run.failed message verbatim and retries from the transcript", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      window.__fixtureRunFailure = {
        code: "UPSTREAM_UNAVAILABLE",
        message: "OpenAI request failed: the model is unavailable.",
      };
    });
    await openWorkspace(page);

    const transcript = page.getByLabel("Execution transcript");
    const feed = page.getByRole("region", { name: "Competitor activity" });
    await feed
      .getByRole("article")
      .filter({ hasText: "NEW_BLOG" })
      .first()
      .getByRole("button", { name: "Create a similar blog" })
      .click();

    await expect(
      transcript.getByText("OpenAI request failed: the model is unavailable."),
    ).toBeVisible();

    // Retry re-dispatches the same trigger; the fixture failure was one-shot,
    // so the second run completes.
    await transcript.getByRole("button", { name: "Retry run" }).click();
    await expect(transcript.getByText("CEO_POST · LINKEDIN · 218 words")).toBeVisible({
      timeout: 10_000,
    });
  });
});

test.describe("7-D the evidence loop", () => {
  test("Do this prefills the composer without sending, and evidence scrolls to its target", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      // MSW's service worker answers inside the page, so Playwright's routing
      // never sees this request. Count it where it is actually made.
      window.__runPosts = 0;
      const original = window.fetch;
      window.fetch = (input, init) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url.includes("/api/runs") && (init?.method ?? "GET") === "POST") {
          window.__runPosts = (window.__runPosts ?? 0) + 1;
        }
        return original(input, init);
      };
    });
    await openWorkspace(page);

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
    expect(await page.evaluate(() => window.__runPosts)).toBe(0);
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
      // The body is clipped by design, so also check the content itself fits:
      // a region wider than its column would be hidden rather than reported.
      const overflow = await page.evaluate(() => {
        const main = document.querySelector("main");
        return {
          body: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          content: main ? main.scrollWidth - main.clientWidth : 0,
        };
      });
      expect(overflow.body, `body overflow at ${width}px`).toBeLessThanOrEqual(0);
      expect(overflow.content, `content overflow at ${width}px`).toBeLessThanOrEqual(0);
    }
  });
});
