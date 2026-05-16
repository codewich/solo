import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
                    latitude: 38.7223,
                    longitude: -9.1393,
                    population: 544851,
                  },
                  score: 91,
                  score_breakdown: {
                    climateScore: 35,
                    attractionScore: 25,
                    popularityScore: 19,
                    affordabilityScore: 12,
                  },
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
                    latitude: 55.6761,
                    longitude: 12.5683,
                    population: 660842,
                  },
                  score: 86,
                  score_breakdown: {
                    climateScore: 30,
                    attractionScore: 25,
                    popularityScore: 20,
                    affordabilityScore: 11,
                  },
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
    expect(screen.getByLabelText("Search radius 1800 km")).toBeInTheDocument();
  });

  it("starts without active date-range recommendations", () => {
    render(<Page />);

    expect(screen.getByText("Select a date range to find matches.")).toBeInTheDocument();
    expect(screen.queryByText("Lisbon, Portugal")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Lisbon city marker")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find destinations" })).toBeDisabled();
  });

  it("enables destination search after selecting a saved range", () => {
    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));

    expect(screen.getByRole("button", { name: "Find destinations" })).toBeEnabled();
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
    expect(screen.getByLabelText("Score breakdown for Lisbon")).toHaveTextContent("Climate: 35");
  });

  it("sends radius and population filters with recommendation requests", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => [
        {
          travel_window: { id: "may", start_date: "2026-05-22", end_date: "2026-05-25" },
          recommendations: [],
        },
      ],
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<Page />);

    fireEvent.change(screen.getByLabelText("Search radius"), { target: { value: "900" } });
    fireEvent.change(screen.getByLabelText("Minimum population"), {
      target: { value: "500000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const payload = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(payload).toEqual(
      expect.objectContaining({
        center_latitude: 51.5072,
        center_longitude: -0.1276,
        radius_km: 900,
        min_population: 500000,
        candidate_limit: 12,
      }),
    );
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
                    population: 544851,
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

  it("lazy-loads intelligence for recommendations after the first three", async () => {
    const observed: Array<{
      callback: IntersectionObserverCallback;
      elements: Element[];
    }> = [];
    class MockIntersectionObserver {
      callback: IntersectionObserverCallback;
      elements: Element[] = [];

      constructor(callback: IntersectionObserverCallback) {
        this.callback = callback;
        observed.push({ callback, elements: this.elements });
      }

      observe(element: Element) {
        this.elements.push(element);
      }

      unobserve(element: Element) {
        this.elements = this.elements.filter((item) => item !== element);
      }

      disconnect() {
        this.elements = [];
      }

      takeRecords() {
        return [];
      }
    }
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);

    const destinations = [
      ["lisbon-pt", "Lisbon", "Portugal", 38.7223, -9.1393],
      ["porto-pt", "Porto", "Portugal", 41.1579, -8.6291],
      ["milan-it", "Milan", "Italy", 45.4642, 9.19],
      ["rome-it", "Rome", "Italy", 41.9028, 12.4964],
    ] as const;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("/recommendations")) {
        return {
          ok: true,
          json: async () => [
            {
              travel_window: { id: "may", start_date: "2026-05-22", end_date: "2026-05-25" },
              recommendations: destinations.map(([id, city, country, latitude, longitude], index) => ({
                travel_window_id: "may",
                destination: {
                  id,
                  city,
                  country,
                  latitude,
                  longitude,
                  population: 500000,
                },
                score: 90 - index,
                reasons: [`${city} fits this window.`],
                caveats: [],
              })),
            },
          ],
        };
      }

      if (url.includes("/destination-intelligence")) {
        const body = JSON.parse(String(init?.body));
        return {
          ok: true,
          json: async () => ({
            destination_city: body.destination_city,
            country: body.country,
            climate: {
              average_temperature_c: 20,
              precipitation_mm: 3,
              sunshine_hours: 7,
              summary: "Mild weather.",
              source: "Open-Meteo",
            },
            attractions: [],
            hotels: {
              average_nightly_price: null,
              median_nightly_price: null,
              currency: null,
              sample_size: 0,
              source: "Amadeus",
              status: "unavailable",
            },
            cost_of_living: {
              currency: "EUR",
              summary: `${body.destination_city} cost summary.`,
              source: "Static Numbeo-compatible seed",
            },
            warnings: [],
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
      expect(screen.getByText("Rome, Italy")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.filter(([url]) => String(url).includes("/destination-intelligence")),
      ).toHaveLength(3);
    });
    expect(screen.queryByText("Rome cost summary.")).not.toBeInTheDocument();

    const romeCard = screen.getByText("Rome, Italy").closest(".card");
    const romeObserver = observed.find((entry) => entry.elements.includes(romeCard as Element));
    expect(romeObserver).toBeDefined();
    act(() => {
      romeObserver?.callback(
        [{ isIntersecting: true, target: romeCard } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Rome cost summary.")).toBeInTheDocument();
    });
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).includes("/destination-intelligence")),
    ).toHaveLength(4);
  });

  it("shows a card spinner while destination intelligence is loading", async () => {
    let resolveIntelligence: (value: {
      ok: boolean;
      json: () => Promise<Record<string, unknown>>;
    }) => void = () => {};
    const intelligenceResponse = new Promise<{
      ok: boolean;
      json: () => Promise<Record<string, unknown>>;
    }>((resolve) => {
      resolveIntelligence = resolve;
    });
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
                    latitude: 38.7223,
                    longitude: -9.1393,
                    population: 544851,
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
        return intelligenceResponse;
      }

      return { ok: true, json: async () => [] };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Page />);

    fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
    expect(screen.getByRole("status", { name: "Loading intelligence for Lisbon" })).toBeInTheDocument();

    resolveIntelligence({
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
        attractions: [{ name: "Belem Tower", category: "attraction", source: "OpenStreetMap" }],
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
          summary: "Lisbon is moderate for Western Europe.",
          source: "Static Numbeo-compatible seed",
        },
      }),
    });

    await waitFor(() => {
      expect(screen.queryByRole("status", { name: "Loading intelligence for Lisbon" })).not.toBeInTheDocument();
    });
    expect(screen.getByText("23C average")).toBeInTheDocument();
  });

  it("shows which intelligence service failed without hiding recommendations", async () => {
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
                    latitude: 38.7223,
                    longitude: -9.1393,
                    population: 544851,
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
          ok: false,
          status: 502,
          json: async () => ({
            detail: {
              step: "climate",
              service: "Open-Meteo",
              message: "Open-Meteo failed during climate lookup: timed out",
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
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load destination intelligence for Lisbon: Open-Meteo failed during climate lookup: timed out",
    );
  });

  it("shows warnings from partial destination intelligence", async () => {
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
                    id: "milan-it",
                    city: "Metropolitan City of Milan",
                    country: "Italy",
                    latitude: 45.4642,
                    longitude: 9.19,
                    population: 1366180,
                  },
                  score: 83,
                  reasons: ["Good rail access and food density."],
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
            destination_city: "Metropolitan City of Milan",
            country: "Italy",
            climate: {
              average_temperature_c: 20,
              precipitation_mm: 3,
              sunshine_hours: 7,
              summary: "Mild weather.",
              source: "Open-Meteo",
            },
            attractions: [],
            hotels: {
              average_nightly_price: null,
              median_nightly_price: null,
              currency: null,
              sample_size: 0,
              source: "Amadeus",
              status: "unavailable",
            },
            cost_of_living: {
              currency: "EUR",
              summary: "Milan is expensive for Italy.",
              source: "Static Numbeo-compatible seed",
            },
            warnings: [
              {
                step: "attractions",
                service: "OpenStreetMap",
                message: "OpenStreetMap failed during attractions lookup: The read operation timed out",
              },
            ],
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
      expect(screen.getByText("20C average")).toBeInTheDocument();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Some destination intelligence is unavailable for Metropolitan City of Milan: OpenStreetMap failed during attractions lookup: The read operation timed out",
    );
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
                    latitude: 41.1579,
                    longitude: -8.6291,
                    population: 231800,
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
