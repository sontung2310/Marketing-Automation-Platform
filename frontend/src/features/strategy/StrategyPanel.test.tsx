import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "../../App";
import { recommendations } from "../../test/fixtures/agents";
import { server } from "../../test/fixtures/server";

describe("Strategy recommendation card", () => {
  it("summarises its signals: ordinal, verbatim priority, title, kinds and Open plan", async () => {
    const [base] = recommendations;
    if (!base) throw new Error("fixture has no recommendation");
    server.use(
      http.get("/api/recommendations", () =>
        HttpResponse.json({
          items: [
            {
              ...base,
              evidence: [
                { id: "trd_seed_004", kind: "trend", note: "AI search visibility ▲142%" },
                { id: "act_seed_028", kind: "activity", note: "Brightlane raised prices 7.1%" },
              ],
            },
          ],
        }),
      ),
    );
    render(<App />);

    const card = await screen.findByRole("article", { name: base.title });
    expect(within(card).getByText("01")).toBeInTheDocument();
    expect(within(card).getByText(base.priority)).toBeInTheDocument();
    expect(within(card).getByRole("heading", { name: base.title })).toBeInTheDocument();
    expect(within(card).getByText(base.insight)).toBeInTheDocument();
    expect(within(card).getByText(`For ${base.audience}`)).toBeInTheDocument();

    const lines = within(card).getAllByRole("listitem");
    expect(lines.map((line) => line.textContent)).toEqual([
      "TrendAI search visibility ▲142%",
      "CompetitorBrightlane raised prices 7.1%",
    ]);
    expect(
      within(card).getByRole("button", { name: `Open plan for ${base.title}` }),
    ).toBeInTheDocument();

    const panel = screen.getByRole("region", { name: "Strategy recommendations" });
    expect(within(panel).getByText("1 pick")).toBeInTheDocument();
  });
});

// The run stream (and so Latest analysis) is covered in Playwright: jsdom has no EventSource.
describe("one Strategy run at a time", () => {
  it("disables every Strategy action while a Strategy run is in flight", async () => {
    const user = userEvent.setup();
    render(<App />);
    const panel = await screen.findByRole("region", { name: "Strategy recommendations" });
    const feed = screen.getByRole("region", { name: "Competitor activity" });
    const [whyItMatters] = await within(feed).findAllByRole("button", { name: "Why it matters" });
    if (!whyItMatters) throw new Error("fixture needs a Why it matters action");

    await user.click(whyItMatters);

    const generate = within(panel).getByRole("button", { name: "Generate strategy" });
    await waitFor(() => expect(generate).toBeDisabled());
    for (const name of ["Why it matters", "Plan a response"]) {
      for (const button of within(feed).queryAllByRole("button", { name })) {
        expect(button).toBeDisabled();
      }
    }
    const execution = within(feed)
      .getAllByRole("button")
      .filter((button) => /similar|Create/i.test(button.textContent ?? ""));
    expect(execution.length).toBeGreaterThan(0);
    for (const button of execution) expect(button).toBeEnabled();
  }, 10_000);
});

describe("Generate strategy", () => {
  it("starts one run however fast it is clicked twice", async () => {
    let posts = 0;
    // A slow 202, so the second click lands while the first request is still pending.
    server.use(
      http.post("/api/runs", async () => {
        posts += 1;
        await delay(300);
        return HttpResponse.json(
          {
            run_id: `run_slow_${posts}`,
            session_id: "ses_slow",
            agent: "STRATEGY",
            intent: "STRATEGY_SYNTHESIS",
            route: { method: "DETERMINISTIC", reason: "Generate strategy", confidence: 1 },
          },
          { status: 202 },
        );
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    const panel = await screen.findByRole("region", { name: "Strategy recommendations" });
    const generate = within(panel).getByRole("button", { name: "Generate strategy" });
    await waitFor(() => expect(generate).toBeEnabled());

    await user.dblClick(generate);

    expect(generate).toBeDisabled();
    await new Promise((resolve) => setTimeout(resolve, 400)); // past the slow 202
    expect(posts).toBe(1);
  });
});
