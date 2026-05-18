import type {
  CitySuggestion,
  DestinationIntelligence,
  DestinationIntelligenceRequest,
  NearestCityRequest,
  Recommendation,
  RecommendationGroup,
  RecommendationRequest,
  RecommendationSearchCity,
  RecommendationSearchCreateRequest,
  RecommendationSearchCreateResponse,
  TravelWindowDeleteRequest,
} from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:45655";

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

async function responseError(response: Response, fallbackMessage: string): Promise<ApiRequestError> {
  let detail: unknown;
  try {
    detail = await response.json();
  } catch {
    detail = undefined;
  }

  const detailMessage =
    typeof detail === "object" &&
    detail !== null &&
    "detail" in detail &&
    typeof detail.detail === "object" &&
    detail.detail !== null &&
    "message" in detail.detail &&
    typeof detail.detail.message === "string"
      ? detail.detail.message
      : fallbackMessage;

  return new ApiRequestError(detailMessage, response.status, detail);
}

export async function fetchRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationGroup[]> {
  const response = await fetch(`${apiBaseUrl}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await responseError(response, `Recommendation request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchCitySuggestions(query: string): Promise<CitySuggestion[]> {
  const response = await fetch(
    `${apiBaseUrl}/geocode/cities?query=${encodeURIComponent(query)}&count=5`,
  );

  if (!response.ok) {
    throw await responseError(response, `City suggestion request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchNearestCity(request: NearestCityRequest): Promise<CitySuggestion> {
  const response = await fetch(`${apiBaseUrl}/geocode/nearest-city`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await responseError(response, `Nearest city request failed with ${response.status}`);
  }

  return response.json();
}

export async function createRecommendationSearch(
  request: RecommendationSearchCreateRequest,
): Promise<RecommendationSearchCreateResponse> {
  const response = await fetch(`${apiBaseUrl}/recommendation-searches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await responseError(response, `Recommendation search failed with ${response.status}`);
  }

  return response.json();
}

export async function deleteTravelWindow(
  windowId: string,
  request: TravelWindowDeleteRequest,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/travel-windows/${encodeURIComponent(windowId)}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await responseError(response, `Travel window delete failed with ${response.status}`);
  }
}

export async function fetchRecommendationSearchCities(
  searchId: string,
): Promise<RecommendationSearchCity[]> {
  const response = await fetch(`${apiBaseUrl}/recommendation-searches/${searchId}/cities`);

  if (!response.ok) {
    throw await responseError(response, `City candidate request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchSavedRecommendationSearchResults(
  searchId: string,
): Promise<Recommendation[]> {
  const response = await fetch(`${apiBaseUrl}/recommendation-searches/${searchId}/recommendations`);

  if (!response.ok) {
    throw await responseError(response, `Saved recommendation request failed with ${response.status}`);
  }

  return response.json();
}

export async function scoreRecommendationSearchCity(
  searchId: string,
  cityId: string,
): Promise<Recommendation> {
  const response = await fetch(
    `${apiBaseUrl}/recommendation-searches/${searchId}/cities/${encodeURIComponent(cityId)}/score`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw await responseError(response, `City scoring request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchRecommendationSearchCityIntelligence(
  searchId: string,
  cityId: string,
): Promise<DestinationIntelligence> {
  const response = await fetch(
    `${apiBaseUrl}/recommendation-searches/${searchId}/cities/${encodeURIComponent(
      cityId,
    )}/intelligence`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw await responseError(
      response,
      `Destination intelligence request failed with ${response.status}`,
    );
  }

  return response.json();
}

export async function fetchDestinationIntelligence(
  request: DestinationIntelligenceRequest,
): Promise<DestinationIntelligence> {
  const response = await fetch(`${apiBaseUrl}/destination-intelligence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await responseError(
      response,
      `Destination intelligence request failed with ${response.status}`,
    );
  }

  return response.json();
}
