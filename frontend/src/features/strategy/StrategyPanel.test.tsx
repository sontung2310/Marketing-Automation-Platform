import { render, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
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
