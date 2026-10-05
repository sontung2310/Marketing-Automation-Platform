import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ExecutionOutput } from "../../api";
import { runs } from "../../test/fixtures/agents";
import { DeliverableCard } from "./DeliverableCard";

const deliverable = (runs[0]?.output as ExecutionOutput | undefined)?.deliverable;
const image = deliverable?.image_suggestions[0];

describe("DeliverableCard", () => {
  it("lists the image suggestions below the opened draft", async () => {
    if (!deliverable || !image)
      throw new Error("The fixture run needs a deliverable with an image");
    render(<DeliverableCard deliverable={deliverable} qualityCheck={null} proposedActions={[]} />);

    expect(screen.queryByText("Image suggestions")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open" }));

    expect(screen.getByText("Image suggestions")).toBeInTheDocument();
    expect(screen.getByText(image.content, { exact: false })).toBeInTheDocument();
    expect(screen.getByText(`(${image.style})`, { exact: false })).toBeInTheDocument();
  });
});
