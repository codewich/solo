from solo_api.destinations import load_destinations
from solo_api.models import (
    Destination,
    Recommendation,
    RecommendationGroup,
    RecommendationRequest,
    TravelWindow,
)


def season_for_month(month: int) -> str:
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    return "winter"


def score_destination(
    destination: Destination, window: TravelWindow, request: RecommendationRequest
) -> tuple[int, list[str]]:
    score = destination.short_stay_score * 10 + destination.solo_friendliness * 5
    reasons: list[str] = []
    season = season_for_month(window.start_date.month)

    if season in destination.seasonal_strengths:
        score += 10
        seasonal_reasons = ", ".join(destination.seasonal_strengths[season][:2])
        reasons.append(f"Strong {season} fit: {seasonal_reasons}.")

    if request.preferences.climate == "warm" and "warm" in destination.tags:
        score += 12
        reasons.append("Matches your preference for warmer destinations.")

    if request.preferences.popularity == "underrated" and "underrated" in destination.tags:
        score += 8
        reasons.append("Leans toward a less obvious city break.")

    for interest, weight in request.preferences.interests.items():
        if interest in destination.tags:
            score += weight * 2
            reasons.append(f"Good match for {interest}.")

    if request.preferences.budget_sensitivity >= 4 and destination.cost_level >= 5:
        score -= 10
        reasons.append("Higher cost may matter for your budget setting.")

    if not reasons:
        reasons.append("Good short-stay fundamentals for this travel window.")

    return score, reasons[:4]


def recommend_destinations(request: RecommendationRequest) -> list[RecommendationGroup]:
    excluded = set(request.excluded_destination_ids)
    candidates = [destination for destination in load_destinations() if destination.id not in excluded]
    groups: list[RecommendationGroup] = []

    for window in request.travel_windows:
        ranked = []
        for destination in candidates:
            score, reasons = score_destination(destination, window, request)
            ranked.append(
                Recommendation(
                    travel_window_id=window.id,
                    destination=destination,
                    score=score,
                    reasons=reasons,
                    caveats=destination.caveats,
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        groups.append(RecommendationGroup(travel_window=window, recommendations=ranked[:5]))

    return groups
