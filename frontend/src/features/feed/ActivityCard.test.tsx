import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ACTIVITY_TYPES, type ActivityType } from "../../api";
import { activities } from "../../test/fixtures/records";
import { ActivityCard } from "./ActivityCard";

/** docs/specs.md §6. The card must render whatever the API computed. */
const PRIMARY_AGENT: Record<ActivityType, "STRATEGY" | "EXECUTION"> = {
  NEW_BLOG: "EXECUTION",
  SOCIAL_POST: "EXECUTION",
  EXECUTIVE_POST: "EXECUTION",
  NEW_PRODUCT: "STRATEGY",
  PRODUCT_REMOVED: "STRATEGY",
  PRICE_CHANGE: "STRATEGY",
  PROMOTION: "STRATEGY",
  CAMPAIGN_LAUNCH: "STRATEGY",
  PAGE_UPDATE: "STRATEGY",
};

const PRIMARY_LABEL: Record<ActivityType, string> = {
  NEW_BLOG: "Create a similar blog",
  SOCIAL_POST: "Create a similar post",
  EXECUTIVE_POST: "Draft a CEO post",
  NEW_PRODUCT: "Plan a response",
  PRODUCT_REMOVED: "Plan a response",
  PRICE_CHANGE: "Plan a response",
  PROMOTION: "Plan a response",
  CAMPAIGN_LAUNCH: "Plan a response",
  PAGE_UPDATE: "Plan a response",
};

function fixtureOf(activityType: ActivityType) {
  const activity = activities.find((item) => item.activity_type === activityType);
  if (!activity) throw new Error(`No fixture activity of type ${activityType}`);
  return activity;
}

describe("ActivityCard", () => {
  it.each(ACTIVITY_TYPES)("renders %s with its mapped primary action", (activityType) => {
    const activity = fixtureOf(activityType);
    const onAction = vi.fn();
    render(<ActivityCard activity={activity} onAction={onAction} />);

    expect(screen.getByText(activityType)).toBeInTheDocument();

    const primary = screen.getByRole("button", { name: PRIMARY_LABEL[activityType] });
    expect(primary).toBeInTheDocument();

    // ui-spec §8: one primary button per card. The filled variant is the
    // only one carrying the brand background.
    const filled = screen
      .getAllByRole("button")
      .filter((button) => button.className.includes("bg-primary"));
    expect(filled).toEqual([primary]);

    primary.click();
    expect(onAction).toHaveBeenCalledWith(
      expect.objectContaining({ agent: PRIMARY_AGENT[activityType], primary: true }),
    );
  });

  it("offers Why it matters only where Execution owns the primary action", () => {
    for (const activityType of ACTIVITY_TYPES) {
      const activity = fixtureOf(activityType);
      const { unmount } = render(<ActivityCard activity={activity} onAction={vi.fn()} />);
      const secondary = screen.queryByRole("button", { name: "Why it matters" });
      const executionOwned = PRIMARY_LABEL[activityType].startsWith("Create");
      expect(Boolean(secondary)).toBe(executionOwned || activityType === "EXECUTIVE_POST");
      unmount();
    }
  });

  it("shows a PRICE_CHANGE as before → after with a signed delta", () => {
    const activity = fixtureOf("PRICE_CHANGE");
    render(<ActivityCard activity={activity} onAction={vi.fn()} />);

    expect(screen.getByText(/\$5,200/)).toBeInTheDocument();
    expect(screen.getByText(/\$5,600/)).toBeInTheDocument();
    expect(screen.getByText(/▲7\.7%/)).toBeInTheDocument();
  });

  it("shows the author and role on an EXECUTIVE_POST", () => {
    const activity = fixtureOf("EXECUTIVE_POST");
    render(<ActivityCard activity={activity} onAction={vi.fn()} />);

    expect(screen.getByText(/Maya Chen, CEO/)).toBeInTheDocument();
  });

  it("badges mock records and simulated records differently", () => {
    const mock = fixtureOf("NEW_BLOG");
    const { unmount } = render(<ActivityCard activity={mock} onAction={vi.fn()} />);
    expect(screen.getByText("MOCK")).toBeInTheDocument();
    expect(screen.queryByText(/SIMULATED/)).not.toBeInTheDocument();
    unmount();

    render(<ActivityCard activity={{ ...mock, is_simulated: true }} onAction={vi.fn()} />);
    expect(screen.getByText(/SIMULATED/)).toBeInTheDocument();
    expect(screen.queryByText("MOCK")).not.toBeInTheDocument();
  });

  it("calls back with the action the API supplied", async () => {
    const onAction = vi.fn();
    const activity = fixtureOf("PRICE_CHANGE");
    render(<ActivityCard activity={activity} onAction={onAction} />);

    screen.getByRole("button", { name: "Plan a response" }).click();

    expect(onAction).toHaveBeenCalledWith(
      expect.objectContaining({ action: "RESPONSE_PLAN", agent: "STRATEGY" }),
    );
  });
});
