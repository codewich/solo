import type { RecommendationGroup, RecommendationRequest } from "./types";

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
