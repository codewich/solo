import type {
  CitySuggestion,
  DestinationIntelligence,
  DestinationIntelligenceRequest,
  RecommendationGroup,
  RecommendationRequest,
} from "./types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:45655";

export async function fetchRecommendations(
  request: RecommendationRequest,
): Promise<RecommendationGroup[]> {
  const response = await fetch(`${apiBaseUrl}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Recommendation request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchCitySuggestions(query: string): Promise<CitySuggestion[]> {
  const response = await fetch(
    `${apiBaseUrl}/geocode/cities?query=${encodeURIComponent(query)}&count=5`,
  );

  if (!response.ok) {
    throw new Error(`City suggestion request failed with ${response.status}`);
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
    throw new Error(`Destination intelligence request failed with ${response.status}`);
  }

  return response.json();
}
