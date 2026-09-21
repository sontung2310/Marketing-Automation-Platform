import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App shell", () => {
  it("renders the three workspace regions", () => {
    render(<App />);

    expect(screen.getByRole("region", { name: "Competitor activity" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Workspace" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Insights" })).toBeInTheDocument();
  });
});
