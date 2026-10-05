import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import type { ProposedAction } from "../../api";
import { server } from "../../test/fixtures/server";
import { ProposedActionRow } from "./ProposedActionRow";

const calendarEntry: ProposedAction = {
  id: "pac_cal",
  deliverable_id: "del_1",
  action_type: "add_to_content_calendar",
  summary: "Add to the content calendar",
  payload: { title: "A post", channel: "LINKEDIN", date: "2026-10-14" },
  status: "PROPOSED",
  receipt: null,
  error: null,
  created_at: "2026-10-06T00:00:00Z",
  updated_at: "2026-10-06T00:00:00Z",
};

describe("ProposedActionRow", () => {
  it("edits a calendar entry's date and shows a failed action's reason", async () => {
    let sent: unknown = null;
    server.use(
      http.post("/api/actions/:actionId/approve", async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({
          ...calendarEntry,
          status: "FAILED",
          error: "The add_to_content_calendar connector failed. The error has been logged.",
        });
      }),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ProposedActionRow action={calendarEntry} />
      </QueryClientProvider>,
    );

    const date = screen.getByLabelText("Date");
    expect(date).toHaveValue("2026-10-14");
    await userEvent.clear(date);
    await userEvent.type(date, "2026-10-15");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("FAILED")).toBeInTheDocument();
    expect(screen.getByText(/connector failed/)).toBeInTheDocument();
    expect(sent).toEqual({ payload_overrides: { date: "2026-10-15" } });
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });
});
