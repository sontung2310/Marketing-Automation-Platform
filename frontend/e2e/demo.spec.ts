import { expect, test, type Locator, type Page } from "@playwright/test";

/**
 * The demo story from docs/specs.md §7, against a real backend, MCP and
 * OpenAI (roadmap 8.1). Run with `npm run demo:e2e` after
 * `scripts/reset_demo.py --yes` (see README "Running the demo"). Assertions
 * are behavioural, not textual: every recommendation and deliverable comes
 * from a live model call, so its wording is never the same run to run.
 */

const RUN_TIMEOUT = 90_000; // a Strategy or Execution run's own p95 (45s / 60s), with slack

function feed(page: Page): Locator {
  return page.getByRole("region", { name: "Competitor activity" });
}

function transcript(page: Page): Locator {
  return page.getByRole("log", { name: "Execution transcript" });
}

function strategyPanel(page: Page): Locator {
  return page.getByRole("region", { name: "Strategy recommendations" });
}

/** The newest transcript turn, waited until the agent's run finishes. */
async function lastCompletedTurn(page: Page): Promise<Locator> {
  const turn = transcript(page).getByRole("article").last();
  await expect(turn.getByRole("button", { name: /Thought for \d+s, used \d+ tools/u })).toBeVisible(
    { timeout: RUN_TIMEOUT },
  );
  return turn;
}

/** Opens each recommendation's plan sheet in turn until one has "Do this"
 * (not every recommendation gets a next_action - MONITOR never does), and
 * returns its ordinal (the niche rule aims for 1-3 picks, so the demo
 * story's illustrative "#2" cannot be assumed - whichever ordinal this
 * opens is the one the chat message resolves by number). */
async function openFirstActionablePlan(page: Page): Promise<number> {
  const cards = strategyPanel(page).getByRole("article");
  const count = await cards.count();
  for (let i = 0; i < count; i++) {
    const card = cards.nth(i);
    await card.getByRole("button", { name: /^Open plan for /u }).click();
    const dialog = page.getByRole("dialog");
    const doThis = dialog.getByRole("button", { name: "Do this" });
    if (await doThis.isVisible()) {
      const label = await dialog.getAttribute("aria-label"); // "Recommendation <ordinal>", read
      await doThis.click(); // before Do this closes the sheet
      return Number(label?.replace(/\D/gu, ""));
    }
    await dialog.getByRole("button", { name: "Close" }).click();
  }
  throw new Error("No recommendation on the panel carries a next_action");
}

test.describe("The 8-step demo story (docs/specs.md §7)", () => {
  test("plays end to end against a live backend", async ({ page }) => {
    test.setTimeout(5 * 60_000); // 8-E: the whole story in 5 minutes or less

    await test.step("1. Open the page", async () => {
      await page.goto("/");
      await expect(page.getByRole("region", { name: "Social listening" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Choose the tenant" })).toHaveText(
        /Marketing Eye/u,
      );
      await expect(page.getByText(/^Last sync /u)).toBeVisible();
      await expect(feed(page).getByRole("article").first()).toBeVisible();
    });

    let signalCard: Locator;
    await test.step("2. A new signal arrives", async () => {
      await page.getByRole("button", { name: "Simulate a signal" }).click();
      await page.getByRole("menuitem", { name: "EXECUTIVE_POST" }).click();
      signalCard = feed(page).getByRole("article").filter({ hasText: "SIMULATED" }).first();
      await expect(signalCard).toBeVisible({ timeout: 10_000 });
    });

    await test.step("3. Why it matters", async () => {
      await signalCard.getByRole("button", { name: "Why it matters" }).click();
      const analysis = page.getByRole("region", { name: "Latest analysis" });
      await expect(analysis).toBeVisible({ timeout: RUN_TIMEOUT });
      await expect(analysis).not.toBeEmpty();
    });

    await test.step("4. Create the response", async () => {
      await signalCard.getByRole("button", { name: "Draft a CEO post" }).click();
      const turn = await lastCompletedTurn(page);
      await expect(turn.getByText("Brand voice")).toBeVisible();
      await expect(turn.getByRole("button", { name: "Approve" })).toBeVisible();
    });

    await test.step("5. Approve", async () => {
      const turn = transcript(page).getByRole("article").last();
      await turn.getByRole("button", { name: "Approve" }).click();
      await expect(turn.getByText("EXECUTED")).toBeVisible({ timeout: 15_000 });
    });

    await test.step("6. Plan a response", async () => {
      const priceCard = feed(page).getByRole("article").filter({ hasText: "PRICE_CHANGE" }).first();
      await expect(priceCard).toBeVisible();
      await priceCard.getByRole("button", { name: "Plan a response" }).click();
      await expect(strategyPanel(page).getByRole("article").first()).toBeVisible({
        timeout: RUN_TIMEOUT,
      });

      await openFirstActionablePlan(page);
      const composer = page.getByLabel("Message the Execution agent");
      await expect(composer).not.toHaveValue("");

      await page.getByRole("button", { name: "Send" }).click();
      await lastCompletedTurn(page); // completion itself is the assertion; wording is non-deterministic
    });

    await test.step("7. Chat, then resolve a recommendation by number", async () => {
      const composer = page.getByLabel("Message the Execution agent");

      await composer.fill("What should we post about next week?");
      await page.getByRole("button", { name: "Send" }).click();
      await lastCompletedTurn(page);
      await expect
        .poll(async () => strategyPanel(page).getByRole("article").count(), {
          timeout: RUN_TIMEOUT,
        })
        .toBeGreaterThan(0);

      const ordinal = await openFirstActionablePlan(page);
      await expect(composer).not.toHaveValue("");

      await composer.fill(`Write the LinkedIn post for recommendation #${ordinal}`);
      await page.getByRole("button", { name: "Send" }).click();
      await lastCompletedTurn(page);
    });

    await test.step("8. Influencers", async () => {
      const influencers = page.getByRole("region", { name: "Influencers" });
      const row = influencers
        .getByRole("row")
        .filter({ has: page.getByRole("button", { name: "Draft outreach" }) })
        .first();
      await row.hover();
      await row.getByRole("button", { name: "Draft outreach" }).click();
      const turn = await lastCompletedTurn(page);
      await expect(turn.getByText("Brand voice")).toBeVisible();
    });
  });
});
