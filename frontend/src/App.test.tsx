import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { server } from "./test/fixtures/server";

describe("workspace shell", () => {
  it("renders the three regions from the fixture API", async () => {
    render(<App />);

    expect(await screen.findByRole("region", { name: "Social listening" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Execution agent" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Strategy recommendations" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Competitor activity" })).toBeInTheDocument();

    expect(await screen.findByRole("button", { name: "Choose the tenant" })).toHaveTextContent(
      "Marketing Eye",
    );
    expect(await screen.findByText(/Last sync/)).toBeInTheDocument();
    expect(await screen.findByText("AI search")).toBeInTheDocument();
  });

  it("shows the Execution empty state before any run", async () => {
    render(<App />);

    expect(
      await screen.findByText("Pick an item from the feed, or ask Execution for a deliverable."),
    ).toBeInTheDocument();
  });

  it("rejects a duplicate tracked keyword without sending a request", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("AI search");
    await user.type(screen.getByLabelText("Add a tracking keyword"), "ai SEARCH");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText('"ai SEARCH" is already tracked.')).toBeInTheDocument();
    expect(screen.getAllByText(/^AI search$/)).toHaveLength(1);
  });

  it("renders a failing region's message verbatim while the others keep working", async () => {
    server.use(
      http.get("/api/trends", () =>
        HttpResponse.json(
          {
            error: { code: "UPSTREAM_UNAVAILABLE", message: "Trends are warming up.", details: {} },
          },
          { status: 503 },
        ),
      ),
    );
    render(<App />);

    const listening = await screen.findByRole("region", { name: "Social listening" });
    expect(await within(listening).findByText("Trends are warming up.")).toBeInTheDocument();
    expect(within(listening).getByRole("button", { name: "Retry" })).toBeInTheDocument();

    const feed = screen.getByRole("region", { name: "Competitor activity" });
    expect((await within(feed).findAllByRole("article")).length).toBeGreaterThan(0);
  });
});
