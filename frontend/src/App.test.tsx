import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { trends } from "./test/fixtures/records";
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
    expect(await screen.findByText("Marketing Strategy")).toBeInTheDocument();
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

    await screen.findByText("Marketing Strategy");
    await user.click(screen.getByRole("button", { name: "Add keyword" }));
    await user.type(screen.getByLabelText("Add a tracking keyword"), "marketing STRATEGY");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText('"marketing STRATEGY" is already tracked.')).toBeInTheDocument();
    expect(screen.getAllByText(/^Marketing Strategy$/)).toHaveLength(1);
  });

  it("removes a keyword from the keyboard and saves the canonical list", async () => {
    const user = userEvent.setup();
    const saved: unknown[] = [];
    server.use(
      http.put("/api/company/tracked-keywords", async ({ request }) => {
        const body = (await request.json()) as { tracked_keywords: string[] };
        saved.push(body.tracked_keywords);
        return HttpResponse.json(body);
      }),
    );
    render(<App />);

    const remove = await screen.findByRole("button", { name: "Stop tracking AI in Marketing" });
    remove.focus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(screen.queryByText("AI in Marketing")).not.toBeInTheDocument());
    expect(saved).toEqual([
      [
        "Marketing Strategy",
        "Digital Marketing Trends",
        "Marketing Automation",
        "Social Media Marketing",
      ],
    ]);
  });

  it("counts the trends each platform tab holds", async () => {
    render(<App />);

    const tabs = await screen.findByRole("tablist", { name: "Platform" });
    await within(tabs).findByRole("tab", { name: `All ${trends.length}` });
    for (const [label, channel] of [
      ["LinkedIn", "LINKEDIN"],
      ["X", "X"],
      ["Reddit", "REDDIT"],
      ["News", "NEWS"],
    ] as const) {
      const expected = trends.filter((trend) => trend.channel === channel).length;
      expect(within(tabs).getByRole("tab", { name: `${label} ${expected}` })).toBeInTheDocument();
    }
  });

  it("shows the company error verbatim instead of skeletons that never resolve", async () => {
    server.use(
      http.get("/api/company", () =>
        HttpResponse.json(
          {
            error: {
              code: "UPSTREAM_UNAVAILABLE",
              message: "The company context is unavailable: Mongo is unreachable.",
              details: {},
            },
          },
          { status: 503 },
        ),
      ),
    );
    render(<App />);

    const listening = await screen.findByRole("region", { name: "Social listening" });
    expect(
      await within(listening).findByText(
        "The company context is unavailable: Mongo is unreachable.",
      ),
    ).toBeInTheDocument();
    expect(within(listening).getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(within(listening).queryByLabelText("Loading tracked keywords")).not.toBeInTheDocument();
  });

  it("badges mock trends and mock influencers", async () => {
    render(<App />);

    const listening = await screen.findByRole("region", { name: "Social listening" });
    expect((await within(listening).findAllByText("MOCK")).length).toBeGreaterThan(0);

    const influencers = await screen.findByRole("region", { name: "Influencers" });
    expect((await within(influencers).findAllByText("MOCK")).length).toBeGreaterThan(0);
  });

  it("keeps one turn when a session restore overlaps a run already in the transcript", async () => {
    const user = userEvent.setup();
    render(<App />);

    const feed = await screen.findByRole("region", { name: "Competitor activity" });
    const cards = await within(feed).findAllByRole("article");
    const blogCard = cards.find((card) => within(card).queryByText("NEW_BLOG"));
    expect(blogCard).toBeDefined();

    await user.click(
      within(blogCard as HTMLElement).getByRole("button", { name: "Create a similar blog" }),
    );

    // Starting the run adopts the session, so GET /sessions/{id} comes back
    // holding that same run. It must not appear twice.
    const transcript = await screen.findByRole("log", { name: "Execution transcript" });
    await waitFor(() =>
      expect(within(transcript).getAllByText("EXECUTION").length).toBeGreaterThan(0),
    );
    expect(within(transcript).getAllByText("CREATE_SIMILAR · BLOG_DRAFT")).toHaveLength(1);
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
