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
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the travel calendar map workflow", () => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: "Solo" })).toBeInTheDocument();
    expect(screen.getByText("Long-weekend map planner")).toBeInTheDocument();
    expect(screen.getByText("Home city: London")).toBeInTheDocument();
    expect(screen.getByText("Candidate travel windows")).toBeInTheDocument();
    expect(screen.getByLabelText("Europe destination map")).toBeInTheDocument();
    expect(screen.getByTestId("maplibre-map")).toBeInTheDocument();
  });

  it("starts without active date-range recommendations", () => {
    render(<Page />);

    expect(screen.getByText("Select a date range to find matches.")).toBeInTheDocument();
    expect(screen.queryByText("Lisbon, Portugal")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Lisbon city marker")).not.toBeInTheDocument();
  });

  it("loads recommendations from the API into the map workspace", async () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
    expect(screen.getByText("Lisbon 91")).toBeInTheDocument();
    expect(screen.getByLabelText("Lisbon city marker")).toBeInTheDocument();
  });

  it("loads destination intelligence for visible recommendations", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("/recommendations")) {
        return {
          ok: true,
          json: async () => [
            {
              travel_window: { id: "may", start_date: "2026-05-22", end_date: "2026-05-25" },
              recommendations: [
                {
                  travel_window_id: "may",
                  destination: {
                    id: "lisbon-pt",
                    city: "Lisbon",
                    country: "Portugal",
                    timezone: "Europe/Lisbon",
                    latitude: 38.7223,
                    longitude: -9.1393,
                    cost_level: 3,
                    short_stay_score: 5,
                    solo_friendliness: 5,
                    tags: [],
                    seasonal_strengths: {},
                    climate_notes: "",
                    caveats: [],
                  },
                  score: 91,
                  reasons: ["Matches your preference for warmer destinations."],
                  caveats: [],
                },
              ],
            },
          ],
        };
      }

      if (url.includes("/destination-intelligence")) {
        return {
          ok: true,
          json: async () => ({
            destination_city: "Lisbon",
            country: "Portugal",
            climate: {
              average_temperature_c: 23,
              precipitation_mm: 4,
              sunshine_hours: 9,
              summary: "Average historical temperature is about 23C for this window.",
              source: "Open-Meteo",
            },
            attractions: [
              { name: "Belem Tower", category: "attraction", source: "OpenStreetMap" },
            ],
            hotels: {
              average_nightly_price: 121,
              median_nightly_price: 118,
              currency: "EUR",
              sample_size: 12,
              source: "Amadeus",
              status: "available",
            },
            cost_of_living: {
              currency: "EUR",
              meal_inexpensive: 14,
              coffee: 2.2,
              local_transport_ticket: 2,
              summary: "Lisbon is moderate for Western Europe.",
              source: "Static Numbeo-compatible seed",
            },
          }),
        };
      }

      return { ok: true, json: async () => [] };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("23C average")).toBeInTheDocument();
    });
    expect(screen.getByText("Belem Tower")).toBeInTheDocument();
    expect(screen.getByText("EUR 118 median hotel")).toBeInTheDocument();
    expect(screen.getByText("Lisbon is moderate for Western Europe.")).toBeInTheDocument();
  });

  it("keeps the calendar read-only until the user starts adding a range", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));

    expect(screen.queryByText(/Draft range:/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toHaveTextContent(
      "22-25 May 2026",
    );
  });

  it("lets the user browse months before selecting dates", () => {
    render(<Page />);

    expect(screen.getByText("May 2026")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next month" }));

    expect(screen.getByText("June 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1 Jun 2026" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Previous month" }));

    expect(screen.getByText("May 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1 May 2026" })).toBeInTheDocument();
  });

  it("highlights the current date when it is visible", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-05-15T12:00:00Z"));

    render(<Page />);

    expect(screen.getByRole("button", { name: "15 May 2026" })).toHaveClass("current-day");

  });

  it("jumps the calendar to a saved range start month when selected", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Next month" }));
    expect(screen.getByText("June 2026")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Select Summer bank holiday/ }));

    expect(screen.getByText("August 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "28 Aug 2026" })).toBeInTheDocument();
  });

  it("highlights the selected saved travel window in the calendar", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));

    expect(screen.getByRole("button", { name: "22 May 2026" })).toHaveClass("selected");
    expect(screen.getByRole("button", { name: "25 May 2026" })).toHaveClass("selected");
    expect(screen.getByRole("button", { name: "26 May 2026" })).not.toHaveClass("selected");

    fireEvent.click(screen.getByRole("button", { name: /Select Summer bank holiday/ }));

    expect(screen.getByText("August 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "28 Aug 2026" })).toHaveClass("selected");
    expect(screen.getByRole("button", { name: "31 Aug 2026" })).toHaveClass("selected");
  });

  it("infers travel pace from the selected date range", () => {
    render(<Page />);

    expect(screen.getByText("Choose a range")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "27 May 2026" }));

    expect(screen.getByText("Wandering pace")).toBeInTheDocument();
    expect(screen.queryByLabelText("Travel pace")).not.toBeInTheDocument();
  });

  it("saves a new draft range when finding recommendations", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("/recommendations")) {
        return {
          ok: true,
          json: async () => [
            {
              travel_window: { id: "range-1", start_date: "2026-05-20", end_date: "2026-05-26" },
              recommendations: [
                {
                  travel_window_id: "range-1",
                  destination: {
                    id: "porto-pt",
                    city: "Porto",
                    country: "Portugal",
                    tags: [],
                    climate_notes: "",
                    caveats: [],
                  },
                  score: 88,
                  reasons: ["Fits the drafted date range."],
                  caveats: [],
                },
              ],
            },
          ],
        };
      }

      return { ok: true, json: async () => [] };
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(Date, "now").mockReturnValue(1);
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Select 20 May-26 May 2026/ })).toBeInTheDocument();
    });
    expect(screen.getByText("Porto, Portugal")).toBeInTheDocument();
    expect(screen.queryByText(/Draft range:/)).not.toBeInTheDocument();
  });

  it("lets the user cancel adding a range", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));

    expect(screen.getByText("Draft range: 20 May-20 May 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "20 May 2026" })).toHaveClass("selected");

    fireEvent.click(screen.getByRole("button", { name: "Cancel range" }));

    expect(screen.queryByText(/Draft range:/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add range" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "20 May 2026" })).not.toHaveClass("selected");
    expect(screen.getByRole("button", { name: "22 May 2026" })).not.toHaveClass("selected");
  });

  it("paginates candidate ranges when the list grows", () => {
    render(<Page />);

    for (let index = 0; index < 7; index += 1) {
      fireEvent.click(screen.getByRole("button", { name: "Add range" }));
      fireEvent.click(screen.getByRole("button", { name: `${10 + index} May 2026` }));
      fireEvent.click(screen.getByRole("button", { name: `${11 + index} May 2026` }));
      fireEvent.click(screen.getByRole("button", { name: "Save draft range" }));
    }

    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next ranges" })).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: /Select 16 May-17 May 2026/ }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next ranges" }));

    expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Select 16 May-17 May 2026/ })).toBeInTheDocument();
  });

  it("keeps calendar draft selection separate from saved ranges", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
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

    fireEvent.click(screen.getByRole("button", { name: "Add range" }));
    fireEvent.click(screen.getByRole("button", { name: "26 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "20 May 2026" }));
    fireEvent.click(screen.getByRole("button", { name: "Save draft range" }));

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
