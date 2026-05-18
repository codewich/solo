import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Toaster } from "@/components/ui/sonner";
import Page from "./page";

const getSessionMock = vi.hoisted(() => vi.fn());

vi.mock("next-auth/react", () => ({
  getSession: getSessionMock,
}));

vi.mock("@/components/auth-button", () => ({
  AuthButton: () => <button type="button">Sign in with Google</button>,
}));

const lisbon = {
  id: "2267057",
  city: "Lisbon",
  country: "Portugal",
  country_code: "PT",
  latitude: 38.7223,
  longitude: -9.1393,
  population: 544851,
};

const porto = {
  id: "2735943",
  city: "Porto",
  country: "Portugal",
  country_code: "PT",
  latitude: 41.1579,
  longitude: -8.6291,
  population: 249633,
};

const madridSuggestion = {
  id: "3117735",
  name: "Madrid",
  country: "Spain",
  country_code: "ES",
  latitude: 40.4168,
  longitude: -3.7038,
  timezone: "Europe/Madrid",
};

function recommendation(destination = lisbon, score = 91) {
  return {
    travel_window_id: "may",
    destination,
    score,
    score_breakdown: {
      climateScore: 35,
      attractionScore: 25,
      popularityScore: 19,
      airQualityScore: 8,
    },
    attraction_count: 7,
    image_url: "https://images.example/lisbon.jpg",
    climate: {
      average_temperature_c: 23,
      average_temperature_min_c: 17,
      average_temperature_max_c: 28,
      precipitation_mm: 4,
      sunshine_hours: 3,
      summary: "Average historical temperature is about 23C for this month.",
      source: "Open-Meteo",
    },
    air_quality: {
      pm25: 8,
      pm10: 14,
      no2: null,
      summary: "Good air quality.",
      source: "OpenAQ",
      status: "available",
    },
    reasons: ["Fits this travel window."],
    caveats: [],
    summary: "Sunny, compact, and easy to navigate.",
  };
}

function intelligence(destination = lisbon) {
  return {
    destination_city: destination.city,
    country: destination.country,
    climate: {
      average_temperature_c: 23,
      average_temperature_min_c: 17,
      average_temperature_max_c: 28,
      precipitation_mm: 4,
      sunshine_hours: 3,
      summary: "Average historical temperature is about 23C for this month.",
      source: "Open-Meteo",
    },
    attractions: [{ name: "Belem Tower", category: "attraction", source: "OpenStreetMap" }],
    warnings: [],
  };
}

function installSearchFetch(overrides?: {
  create?: () => Promise<ResponseLike>;
  saved?: () => Promise<ResponseLike>;
  cities?: () => Promise<ResponseLike>;
  score?: (cityId: string) => Promise<ResponseLike>;
  details?: (cityId: string) => Promise<ResponseLike>;
}) {
  const fetchMock = vi.fn(async (url: string) => {
    const path = String(url);
    if (path.endsWith("/recommendation-searches")) {
      return overrides?.create?.() ?? ok({ id: "search-1", travel_window_id: "may", status: "created" });
    }
    if (path.includes("/travel-windows/")) {
      return ok({});
    }
    if (path.includes("/holidays/regions")) {
      return ok([
        { country_code: "GB", region_code: "gb-eng", name: "England" },
        { country_code: "GB", region_code: "gb-sct", name: "Scotland" },
      ]);
    }
    if (path.includes("/holidays?")) {
      return ok([{ date: "2026-05-25", name: "Spring bank holiday", country_code: "GB", region_code: "gb-eng" }]);
    }
    if (path.endsWith("/recommendation-searches/search-1/recommendations")) {
      return overrides?.saved?.() ?? ok([]);
    }
    if (path.endsWith("/recommendation-searches/search-1/cities")) {
      return (
        overrides?.cities?.() ??
        ok([
          { search_id: "search-1", destination: lisbon },
          { search_id: "search-1", destination: porto },
        ])
      );
    }
    if (path.includes("/recommendation-searches/search-1/cities/") && path.endsWith("/score")) {
      const cityId = path.split("/cities/")[1].split("/")[0];
      return overrides?.score?.(cityId) ?? ok(recommendation(cityId === porto.id ? porto : lisbon, cityId === porto.id ? 86 : 91));
    }
    if (path.includes("/recommendation-searches/search-1/cities/") && path.endsWith("/intelligence")) {
      const cityId = path.split("/cities/")[1].split("/")[0];
      return overrides?.details?.(cityId) ?? ok(intelligence(cityId === porto.id ? porto : lisbon));
    }
    if (path.includes("/geocode/cities")) {
      return ok([madridSuggestion]);
    }
    return ok([]);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

type ResponseLike = {
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
};

function ok(payload: unknown): ResponseLike {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  };
}

function fail(status: number, message: string): ResponseLike {
  return {
    ok: false,
    status,
    json: async () => ({ detail: { message } }),
  };
}

async function selectSpringWindow() {
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toBeInTheDocument();
  });
  fireEvent.click(screen.getByRole("button", { name: /Select Spring bank holiday/ }));
}

describe("Solo homepage", () => {
  beforeEach(() => {
    getSessionMock.mockResolvedValue({
      expires: "2026-12-31T00:00:00.000Z",
      user: { email: "solo@example.com", name: "Solo User" },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    getSessionMock.mockReset();
  });

  it("renders the map workflow with home city controls in the top bar", async () => {
    installSearchFetch();

    render(<Page />);

    expect(screen.getByRole("heading", { name: "Solo" })).toBeInTheDocument();
    expect(screen.getByText("Long-weekend map planner")).toBeInTheDocument();
    expect(screen.getByLabelText("Home city")).toHaveValue("London");
    expect(screen.getByRole("button", { name: "Use current location" })).toBeInTheDocument();
    expect(screen.getByText("Candidate travel windows")).toBeInTheDocument();
    expect(screen.getByLabelText("Europe destination map")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find destinations" })).toBeDisabled();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Select Spring bank holiday/ })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Holiday region")).toHaveValue("gb-eng");
    });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sign in with Google" })).toBeInTheDocument();
    });
  });

  it("loads holidays for the visible calendar year and selected region", async () => {
    const fetchMock = installSearchFetch();
    render(<Page />);

    await waitFor(() => {
      expect(screen.getByLabelText("Holiday region")).toHaveValue("gb-eng");
    });
    fireEvent.change(screen.getByLabelText("Holiday region"), {
      target: { value: "gb-sct" },
    });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("/holidays?country=GB&year=2026&region=gb-sct"),
        ),
      ).toBe(true);
    });
  });

  it("does not show date ranges when the user is signed out", async () => {
    getSessionMock.mockResolvedValueOnce(null);
    installSearchFetch();

    render(<Page />);

    await waitFor(() => {
      expect(screen.getByText("Sign in to add and save travel windows.")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Select Spring bank holiday/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find destinations" })).toBeDisabled();
  });

  it("deletes a date range from the API before removing it from the saved range list", async () => {
    const fetchMock = installSearchFetch();
    render(<Page />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Remove Spring bank holiday/ })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Remove Spring bank holiday/ }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Select Spring bank holiday/ })).not.toBeInTheDocument();
    });
    const deleteCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/travel-windows/may") && init?.method === "DELETE",
    );
    expect(deleteCall).toBeDefined();
    expect(JSON.parse(String(deleteCall?.[1]?.body))).toEqual({
      user_email: "solo@example.com",
      provider_subject: "solo@example.com",
    });
  });

  it("loads candidate cards first, then fills them as scoring and details return", async () => {
    let resolveScore: (value: ResponseLike) => void = () => {};
    let resolveDetails: (value: ResponseLike) => void = () => {};
    const scoreResponse = new Promise<ResponseLike>((resolve) => {
      resolveScore = resolve;
    });
    const detailsResponse = new Promise<ResponseLike>((resolve) => {
      resolveDetails = resolve;
    });
    const fetchMock = installSearchFetch({
      cities: async () => ok([{ search_id: "search-1", destination: lisbon }]),
      score: async () => scoreResponse,
      details: async () => detailsResponse,
    });
    render(<Page />);

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Lisbon, Portugal")).toBeInTheDocument();
    });
    expect(screen.getAllByLabelText("Loading score").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Loading destination score").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Loading destination details").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Loading destination intelligence").length).toBeGreaterThan(0);

    resolveScore(ok(recommendation(lisbon, 91)));
    resolveDetails(ok(intelligence(lisbon)));

    await waitFor(() => {
      expect(screen.getByText("Sunny, compact, and easy to navigate.")).toBeInTheDocument();
    });
    expect(screen.getByText("17-28C")).toBeInTheDocument();
    expect(screen.getByText("4 mm rain")).toBeInTheDocument();
    expect(screen.getByText("3 h sun")).toBeInTheDocument();
    expect(screen.getByText("Good air")).toHaveClass("air-good");
    expect(screen.getByText("Belem Tower")).toBeInTheDocument();
    expect(screen.queryByText(/hotel/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/affordability/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Lisbon city marker")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith(`/${lisbon.id}/score`))).toBe(true);
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith(`/${lisbon.id}/intelligence`))).toBe(true);
  });

  it("sends search parameters, home city, and excluded city ids to the create-search endpoint", async () => {
    const fetchMock = installSearchFetch();
    render(<Page />);

    fireEvent.change(screen.getByLabelText("Minimum population"), {
      target: { value: "500000" },
    });
    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    const createCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/recommendation-searches"),
    );
    const payload = JSON.parse(String(createCall?.[1]?.body));
    expect(payload).toEqual(
      expect.objectContaining({
        home_city_id: "2643743",
        radius_km: 1800,
        min_population: 500000,
        candidate_limit: 10,
        excluded_city_ids: ["2643743"],
        user_email: "solo@example.com",
        user_name: "Solo User",
        provider_subject: "solo@example.com",
      }),
    );
  });

  it("adds excluded cities from autocomplete and removes them as tags", async () => {
    const fetchMock = installSearchFetch();
    render(<Page />);

    fireEvent.change(screen.getByLabelText("Exclude cities"), {
      target: { value: "Mad" },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Madrid, Spain" })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Madrid, Spain" }));

    expect(screen.getByLabelText("Excluded cities")).toHaveTextContent("Madrid, Spain");
    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });
    let createCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/recommendation-searches"),
    );
    let payload = JSON.parse(String(createCall?.[1]?.body));
    expect(payload.excluded_city_ids).toEqual(["2643743", "3117735"]);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Find destinations" })).toBeEnabled();
    });
    fireEvent.click(screen.getByRole("button", { name: "Remove Madrid exclusion" }));
    fireEvent.click(screen.getByRole("button", { name: /Find destinations/ }));

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/recommendation-searches")),
      ).toHaveLength(2);
    });
    createCall = fetchMock.mock.calls
      .filter(([url]) => String(url).endsWith("/recommendation-searches"))
      .at(-1);
    payload = JSON.parse(String(createCall?.[1]?.body));
    expect(payload.excluded_city_ids).toEqual(["2643743"]);
  });

  it("shows real search progress on the find destinations button", async () => {
    let resolveCities: (value: ResponseLike) => void = () => {};
    const citiesResponse = new Promise<ResponseLike>((resolve) => {
      resolveCities = resolve;
    });
    installSearchFetch({
      cities: () => citiesResponse,
    });
    render(<Page />);

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Loading list of cities/ })).toBeDisabled();
    });
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();

    resolveCities(ok([{ search_id: "search-1", destination: lisbon }]));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Find destinations/ })).toBeEnabled();
    });
  });

  it("uses a persistent top toast for recommendation errors", async () => {
    installSearchFetch({
      create: async () => fail(400, "City catalog is not ready."),
    });

    render(
      <>
        <Page />
        <Toaster position="top-center" richColors />
      </>,
    );

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("City catalog is not ready.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Could not load recommendations.")).not.toBeInTheDocument();
  });

  it("shows N/A when destination details fail", async () => {
    installSearchFetch({
      details: async () => fail(502, "OpenStreetMap timed out."),
    });

    render(<Page />);

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);
    });
  });

  it("shows a card-level retry button only for city scoring failures", async () => {
    let attempts = 0;
    installSearchFetch({
      score: async () => {
        attempts += 1;
        if (attempts <= 3) {
          return fail(502, "Scoring failed.");
        }
        return ok(recommendation(lisbon, 88));
      },
      cities: async () => ok([{ search_id: "search-1", destination: lisbon }]),
    });

    render(<Page />);

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByText("Scoring failed.")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("Sunny, compact, and easy to navigate.")).toBeInTheDocument();
    });
    expect(attempts).toBe(4);
  });

  it("disables range selection while searching", async () => {
    let resolveCities: (value: ResponseLike) => void = () => {};
    const citiesResponse = new Promise<ResponseLike>((resolve) => {
      resolveCities = resolve;
    });
    installSearchFetch({ cities: () => citiesResponse });
    render(<Page />);

    await selectSpringWindow();
    fireEvent.click(screen.getByRole("button", { name: "Find destinations" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Select Summer bank holiday/ })).toBeDisabled();
    });

    resolveCities(ok([]));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Find destinations/ })).toBeEnabled();
    });
  });
});
