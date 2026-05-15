import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Page from "./page";

describe("Solo homepage", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        return {
          ok: true,
          json: async () => [
            {
              travel_window: { id: "may", start_date: "2026-05-23", end_date: "2026-05-25" },
              recommendations: [
                {
                  travel_window_id: "may",
                  destination: {
                    id: "lisbon-pt",
                    city: "Lisbon",
                    country: "Portugal",
                    tags: [],
                    climate_notes: "",
                    caveats: [],
                  },
                  score: 91,
                  reasons: ["Matches your preference for warmer destinations."],
                  caveats: [],
                },
              ],
            },
            {
              travel_window: {
                id: "august",
                start_date: "2026-08-28",
                end_date: "2026-08-31",
              },
              recommendations: [
                {
                  travel_window_id: "august",
                  destination: {
                    id: "copenhagen-dk",
                    city: "Copenhagen",
                    country: "Denmark",
                    tags: [],
                    climate_notes: "",
                    caveats: [],
                  },
                  score: 86,
                  reasons: ["Long daylight fits this summer window."],
                  caveats: [],
                },
              ],
            },
          ],
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the travel calendar map workflow", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Solo" })).toBeInTheDocument();
    expect(screen.getByText("Long-weekend map planner")).toBeInTheDocument();
    expect(screen.getByLabelText("Home city")).toBeInTheDocument();
    expect(screen.getByText("Candidate travel windows")).toBeInTheDocument();
    expect(screen.getByLabelText("Europe destination map")).toBeInTheDocument();
  });

  it("loads recommendations from the API into the map workspace", async () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
    expect(screen.getByText("Lisbon 91")).toBeInTheDocument();
  });

  it("keeps calendar draft selection separate from saved ranges", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));

    expect(screen.getByText("Draft range: 26 May-26 May 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toHaveTextContent(
      "22-25 May 2026",
    );

    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));

    expect(screen.getByText("Draft range: 20 May-26 May 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toHaveTextContent(
      "22-25 May 2026",
    );
  });

  it("uses the selected travel window for recommendation emphasis", async () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Summer bank holiday/ }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Copenhagen, Denmark")).toBeInTheDocument();
    });
    expect(screen.getByText("Copenhagen 86")).toBeInTheDocument();
    expect(screen.queryByText("Lisbon, Portugal")).not.toBeInTheDocument();
  });

  it("lets the user add, rename, archive, and remove ranges", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "Add range" }));

    expect(screen.getByRole("button", { name: /Select 20 May-26 May 2026/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toHaveTextContent(
      "22-25 May 2026",
    );

    fireEvent.click(screen.getByRole("button", { name: /Rename 20 May-26 May 2026/ }));
    fireEvent.change(screen.getByLabelText("Range label"), {
      target: { value: "Warm food sprint" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save range" }));

    expect(screen.getByRole("button", { name: /Select Warm food sprint/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Archive Warm food sprint/ }));
    expect(screen.getByText("archived")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Remove Warm food sprint/ }));
    expect(screen.queryByRole("button", { name: /Select Warm food sprint/ })).not.toBeInTheDocument();
  });
});
