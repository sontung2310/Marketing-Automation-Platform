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

/** The ui-spec §6 accessibility gate, in whichever theme the page is in. */
async function expectAccessible(page: Page): Promise<void> {
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
      "Marketing Strategy",
      "Digital Marketing Trends",
      "AI in Marketing",
      "Marketing Automation",
      "Social Media Marketing",
    ]) {
      await expect(page.getByRole("listitem").filter({ hasText: keyword })).toBeVisible();
    }

    await expect(
      page.getByText("Pick an item from the feed, or ask Execution for a deliverable."),
    ).toBeVisible();

    // Every panel header carries its icon tile, title and count or status pill.
    for (const [region, pill] of [
      ["Social listening", /5 keywords · \d+ trends/],
      ["Influencers", /\d+ ranked/],
      ["Execution agent", /0 requests/],
      ["Strategy recommendations", /\d+ (open|picks?)/],
      ["Competitor activity", /\d+ new/],
    ] as const) {
      const header = page.getByRole("region", { name: region }).locator("> div").first();
      await expect(header.getByRole("heading", { name: region })).toBeVisible();
      await expect(header.locator("svg")).toHaveCount(1);
      await expect(header.getByText(pill)).toBeVisible();
    }

    expect(consoleErrors).toEqual([]);
  });

  test("passes an axe accessibility scan with no violations", async ({ page }) => {
    await openWorkspace(page);
    await expectAccessible(page);
  });
});

test.describe("7-J tracked keywords", () => {
  test("a row's remove control shows on keyboard focus and removes the term", async ({ page }) => {
    await openWorkspace(page);
    const remove = page.getByRole("button", { name: "Stop tracking AI in Marketing" });
    await expect(remove).toHaveCSS("opacity", "0");

    await remove.focus();
    await expect(remove).toHaveCSS("opacity", "1");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("listitem").filter({ hasText: "AI in Marketing" })).toHaveCount(0);
  });
});

test.describe("7-G light and dark themes", () => {
  const theme = (page: Page) => page.evaluate(() => document.documentElement.dataset.theme);
  const pageGround = (page: Page) =>
    page.evaluate(() => getComputedStyle(document.body).backgroundColor);

  test("follows a dark system preference and passes the axe scan", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await openWorkspace(page);

    expect(await theme(page)).toBe("dark");
    expect(await pageGround(page)).toBe("rgb(17, 18, 20)");
    await page.getByRole("button", { name: "Choose the theme" }).click();
    await expect(page.getByRole("menuitemradio", { name: "System" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    await page.keyboard.press("Escape");
    await expectAccessible(page);
  });

  test("resolves the theme before the app renders", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    // Block the bundle: only index.html's pre-paint script can set the theme.
    await page.route(/\/src\/main\.tsx/, (route) => route.abort());
    await page.goto("/");
    expect(await theme(page)).toBe("dark");
  });

  test("a chosen theme overrides the system, persists, and System clears it", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await openWorkspace(page);
    expect(await theme(page)).toBe("light");

    const pick = async (option: string) => {
      await page.getByRole("button", { name: "Choose the theme" }).click();
      await page.getByRole("menuitemradio", { name: option }).click();
    };

    await pick("Dark");
    expect(await theme(page)).toBe("dark");
    await page.reload();
    await expect(page.getByRole("region", { name: "Social listening" })).toBeVisible();
    expect(await theme(page)).toBe("dark");

    await pick("System");
    expect(await theme(page)).toBe("light");
  });
});

test.describe("7-A keyboard focus is visible on every control", () => {
  test("the composer shows a focus ring", async ({ page }) => {
    await openWorkspace(page);

    const composer = page.getByLabel("Message the Execution agent");
    await composer.focus();
    // The ring follows the rounded wrapper rather than the bare field.
    const ringTarget = page.locator("div:has(> #composer)").last();

    // ui-spec §6: a visible 2px focus ring using --border-focus. An
    // `outline-none` utility beats the global :focus-visible rule, because
    // Tailwind's utilities layer wins over the base layer.
    const ring = await ringTarget.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        style: style.outlineStyle,
        width: style.outlineWidth,
        color: style.outlineColor,
      };
    });
    expect(ring.style).not.toBe("none");
    expect(parseFloat(ring.width)).toBeGreaterThanOrEqual(2);
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

    const transcript = page.getByRole("log", { name: "Execution transcript" });

    // docs/specs.md §8: a run never goes more than 10 s without a UI update.
    // The elapsed counter ticks every second on its own, so it is stripped
    // out: what is measured is agent-driven change — steps, tool rows, the
    // answer and the deliverable. Sampling runs until the run finishes or the
    // window closes, and the window is wider than the budget so a stall is
    // actually reachable.
    const AGENT_UPDATE_BUDGET_MS = 10_000;
    const SAMPLE_WINDOW_MS = 15_000;
    const structure = (text: string) =>
      text.replace(/Thought for \d+s/g, "").replace(/\b\d+s\b/g, "");

    const samples: { at: number; text: string }[] = [];
    const started = Date.now();
    await blogCard.getByRole("button", { name: "Create a similar blog" }).click();

    // Scope to this run's own turn: the session restore brings an older,
    // already-finished turn into the same transcript.
    const turn = transcript.getByRole("article", {
      name: "EXECUTION CREATE_SIMILAR · BLOG_DRAFT",
    });
    const finished = turn.getByText("CEO_POST · LINKEDIN · 218 words");
    while (Date.now() - started < SAMPLE_WINDOW_MS) {
      const text = await turn.innerText().catch(() => "");
      samples.push({ at: Date.now() - started, text: structure(text) });
      if (await finished.isVisible().catch(() => false)) break;
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
    expect(longestGap).toBeLessThan(AGENT_UPDATE_BUDGET_MS);

    await expect(turn).toBeVisible();

    const thinking = turn.getByRole("button", { name: /Thought for \d+s, used \d+ tools/ });
    await expect(thinking).toBeVisible();
    await expect(turn.getByText(/Drafted in first person/)).toBeVisible();
    await expect(turn.getByText("CEO_POST · LINKEDIN · 218 words")).toBeVisible();

    // Expanding the collapsed line reveals the reasoning steps and one row per tool.
    await thinking.click();
    await expect(turn.getByText("Loading company context")).toBeVisible();
    await expect(turn.getByText("search_competitor_activity")).toBeVisible();

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

test.describe("6.2 a run stream closed mid-run", () => {
  test("resumes from Last-Event-ID and ends exactly like an uninterrupted run", async ({
    browser,
  }) => {
    const finalTurn = async (cutAfterSeq: number | null): Promise<string> => {
      const page = await browser.newPage();
      if (cutAfterSeq !== null) {
        await page.addInitScript((cut) => {
          window.__fixtureRunStreamCut = cut;
        }, cutAfterSeq);
      }
      await openWorkspace(page);
      const blogCard = page
        .getByRole("region", { name: "Competitor activity" })
        .getByRole("article")
        .filter({ hasText: "NEW_BLOG" })
        .first();
      await blogCard.getByRole("button", { name: "Create a similar blog" }).click();
      const turn = page
        .getByRole("log", { name: "Execution transcript" })
        .getByRole("article", { name: "EXECUTION CREATE_SIMILAR · BLOG_DRAFT" });
      await expect(turn.getByText("CEO_POST · LINKEDIN · 218 words")).toBeVisible({
        timeout: 20_000,
      });
      // Compare finished runs: the spinner goes once run.completed has arrived.
      await expect(turn.locator(".animate-spin")).toHaveCount(0, { timeout: 10_000 });
      const text = (await turn.innerText()).replace(/\b\d+s\b/g, "");
      await page.close();
      return text;
    };

    const uninterrupted = await finalTurn(null);
    const resumed = await finalTurn(3);
    expect(resumed).toBe(uninterrupted);
  });
});

test.describe("6.2 the daily run cap", () => {
  test("shows the RATE_LIMITED message verbatim in the transcript", async ({ page }) => {
    await page.addInitScript(() => {
      window.__fixtureFailures = [
        {
          path: "/api/runs",
          method: "post",
          status: 429,
          code: "RATE_LIMITED",
          message: "The demo's daily run limit is reached. Try again tomorrow.",
        },
      ];
    });
    await openWorkspace(page);

    await page.getByLabel("Message the Execution agent").fill("Write a LinkedIn post on AI search");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(
      page
        .getByRole("log", { name: "Execution transcript" })
        .getByText("The demo's daily run limit is reached. Try again tomorrow."),
    ).toBeVisible();
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

    const transcript = page.getByRole("log", { name: "Execution transcript" });
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

test.describe("7-C a failed Strategy run", () => {
  test("keeps its message and Retry in the Strategy panel", async ({ page }) => {
    await page.addInitScript(() => {
      window.__fixtureRunFailure = {
        code: "UPSTREAM_UNAVAILABLE",
        message: "OpenAI request failed: the model is unavailable.",
      };
    });
    await openWorkspace(page);

    const strategy = page.getByRole("region", { name: "Strategy recommendations" });
    await page
      .getByRole("region", { name: "Competitor activity" })
      .getByRole("article")
      .filter({ hasText: "PRICE_CHANGE" })
      .first()
      .getByRole("button", { name: "Plan a response" })
      .click();

    const failure = strategy.getByRole("alert");
    await expect(failure).toContainText("OpenAI request failed: the model is unavailable.");
    await failure.getByRole("button", { name: "Retry run" }).click();
    await expect(failure).toBeHidden({ timeout: 10_000 });
  });
});

test.describe("7-C retrying a message run", () => {
  test("does not echo the marketer's message twice", async ({ page }) => {
    await page.addInitScript(() => {
      window.__fixtureRunFailure = { code: "INTERNAL", message: "Run failed." };
    });
    await openWorkspace(page);

    const transcript = page.getByRole("log", { name: "Execution transcript" });
    await page.getByLabel("Message the Execution agent").fill("Write a LinkedIn post on AI search");
    await page.getByRole("button", { name: "Send" }).click();
    await transcript.getByRole("button", { name: "Retry run" }).click();
    await expect(transcript.getByText("Run failed.")).toHaveCount(1);
    await expect(transcript.getByText("Write a LinkedIn post on AI search")).toHaveCount(1);
  });
});

test.describe("7-D the evidence loop", () => {
  test("Do this prefills the composer without sending, sends the recommendation unedited, and evidence scrolls to its target", async ({
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
          window.__runBodies = [...(window.__runBodies ?? []), String(init?.body)];
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

    // Sent unedited, the draft runs the recommendation itself, not a chat guess.
    await page.getByRole("button", { name: "Send" }).click();
    await expect.poll(() => page.evaluate(() => window.__runPosts)).toBe(1);
    const [body = ""] = await page.evaluate(() => window.__runBodies ?? []);
    expect(JSON.parse(body).trigger).toMatchObject({ kind: "RECOMMENDATION", action: "DO_THIS" });
    await expect(
      page
        .getByRole("log", { name: "Execution transcript" })
        .getByText("Write the LinkedIn post for recommendation #1"),
    ).toBeVisible();
  });
});

test.describe("7-D an edited Do this draft", () => {
  test("goes to the router as chat, not as the recommendation", async ({ page }) => {
    await page.addInitScript(() => {
      window.__runBodies = [];
      const original = window.fetch;
      window.fetch = (input, init) => {
        const url = typeof input === "string" ? input : input.toString();
        if (url.includes("/api/runs") && (init?.method ?? "GET") === "POST") {
          window.__runBodies = [...(window.__runBodies ?? []), String(init?.body)];
        }
        return original(input, init);
      };
    });
    await openWorkspace(page);

    await page.getByRole("button", { name: /Hold price, publish the reasoning/ }).click();
    await page.getByRole("button", { name: "Do this" }).click();
    const composer = page.getByLabel("Message the Execution agent");
    await composer.fill("Write the LinkedIn post for recommendation #1, under 100 words");
    await page.getByRole("button", { name: "Send" }).click();

    await expect.poll(() => page.evaluate(() => window.__runBodies?.length)).toBe(1);
    const [body = ""] = await page.evaluate(() => window.__runBodies ?? []);
    const request = JSON.parse(body) as { message?: string; trigger?: unknown };
    expect(request.trigger).toBeUndefined();
    expect(request.message).toBe("Write the LinkedIn post for recommendation #1, under 100 words");
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

  test("long clarification options wrap inside a narrow transcript", async ({ page }) => {
    await openWorkspace(page);
    await page.setViewportSize({ width: 760, height: 800 });
    await page
      .getByRole("tablist", { name: "Workspace region" })
      .getByRole("tab", { name: "Workspace" })
      .click();

    await page.getByLabel("Message the Execution agent").fill("Audit our service pages");
    await page.getByRole("button", { name: "Send" }).click();

    const transcript = page.getByRole("log", { name: "Execution transcript" });
    const option = transcript.getByRole("button", { name: /^Audit these service pages/ });
    await expect(option).toBeVisible();
    const [optionBox, transcriptBox] = await Promise.all([
      option.boundingBox(),
      transcript.boundingBox(),
    ]);
    expect(optionBox && transcriptBox && optionBox.width <= transcriptBox.width).toBe(true);
    expect(optionBox?.height ?? 0).toBeGreaterThan(32); // more than one line
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
