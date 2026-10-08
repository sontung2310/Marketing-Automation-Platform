import { fireEvent, render, screen, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { App } from "../../App";
import { initials } from "../../lib/format";
import { influencers } from "../../test/fixtures/records";
import { server } from "../../test/fixtures/server";

describe("Influencer avatars", () => {
  it("show the image, and the monogram when it is missing or fails to load", async () => {
    const [withImage, withoutImage, broken] = influencers;
    if (!withImage || !withoutImage || !broken) throw new Error("fixture needs 3 influencers");
    server.use(
      http.get("/api/influencers", () =>
        HttpResponse.json({
          items: [
            { ...withImage, avatar_url: "https://pbs.example/one.jpg" },
            { ...withoutImage, avatar_url: null },
            { ...broken, avatar_url: "https://pbs.example/missing.jpg" },
          ],
        }),
      ),
    );
    render(<App />);

    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    const [first, second, third] = rows.map((row) => row.querySelector("td"));
    if (!first || !second || !third) throw new Error("expected three rows");

    expect(first.querySelector("img")).toHaveAttribute("src", "https://pbs.example/one.jpg");
    expect(first.querySelector("img")).toHaveAttribute("alt", "");
    expect(second.querySelector("img")).toBeNull();
    expect(second.querySelector('[aria-hidden="true"]')).toHaveTextContent(
      initials(withoutImage.name),
    );

    const failing = third.querySelector("img");
    if (!failing) throw new Error("expected an image before it fails");
    fireEvent.error(failing);
    expect(third.querySelector("img")).toBeNull();
    expect(third.querySelector('[aria-hidden="true"]')).toHaveTextContent(initials(broken.name));
  });
});
