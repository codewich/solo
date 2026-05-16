from datetime import date
from typing import Any

from solo_api.destinations import load_destinations
from solo_api.models import (
    AttractionSummary,
    ClimateSummary,
    CoordinatesResult,
    CostOfLivingSummary,
    Destination,
    Recommendation,
    RecommendationGroup,
    RecommendationRequest,
    RecommendationScoreBreakdown,
    RecommendedDestination,
    TravelWindow,
)
from solo_api.recommendation_signals import DestinationSignals, get_destination_signals


def season_for_month(month: int) -> str:
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    if month in {9, 10, 11}:
        return "autumn"
    return "winter"


def _signals_from_value(value: DestinationSignals | dict[str, Any]) -> DestinationSignals:
    if isinstance(value, DestinationSignals):
        return value

    return DestinationSignals(
        climate=value["climate"],
        attractions=value.get("attractions", []),
        summary=value.get("summary"),
        cost_of_living=value["cost_of_living"],
        warnings=value.get("warnings", []),
    )


def _climate_score(climate: ClimateSummary) -> int:
    if climate.average_temperature_c is None:
        score = 18
    elif 18 <= climate.average_temperature_c <= 28:
        score = 35
    elif 12 <= climate.average_temperature_c < 18 or 28 < climate.average_temperature_c <= 32:
        score = 26
    elif 5 <= climate.average_temperature_c < 12 or 32 < climate.average_temperature_c <= 36:
        score = 16
    else:
        score = 8

    if climate.precipitation_mm is not None:
        if climate.precipitation_mm >= 25:
            score -= 12
        elif climate.precipitation_mm >= 12:
            score -= 6

    return max(0, min(35, score))


def _attraction_score(attractions: list[AttractionSummary], destination: Destination) -> int:
    score = min(25, len(attractions) * 4)
    if not attractions:
        seed_matches = {"history", "museums", "architecture", "nature"}.intersection(destination.tags)
        score = min(14, len(seed_matches) * 4)
    return score


def _popularity_score(summary: str | None, destination: Destination) -> int:
    score = 0
    if summary:
        score += min(15, max(5, len(summary) // 80))
    if "popular" in destination.tags:
        score += 5
    if "underrated" in destination.tags:
        score += 2
    return min(20, score)


def _affordability_score(cost: CostOfLivingSummary, destination: Destination) -> int:
    score = max(0, 22 - destination.cost_level * 4)
    if cost.meal_inexpensive is not None:
        if cost.meal_inexpensive <= 12:
            score += 4
        elif cost.meal_inexpensive >= 22:
            score -= 4
    return max(0, min(20, score))


def _estimated_daily_budget(cost: CostOfLivingSummary, destination: Destination) -> float | None:
    if cost.meal_inexpensive is not None and cost.coffee is not None and cost.local_transport_ticket is not None:
        return round(cost.meal_inexpensive * 2 + cost.coffee * 2 + cost.local_transport_ticket * 2, 2)
    return float(destination.cost_level * 35)


def _best_months_to_visit(destination: Destination) -> list[str]:
    month_names = {
        "spring": ["March", "April", "May"],
        "summer": ["June", "July", "August"],
        "autumn": ["September", "October", "November"],
        "winter": ["December", "January", "February"],
    }
    months: list[str] = []
    for season in destination.seasonal_strengths:
        months.extend(month_names.get(season, []))
    return months[:6]


def score_destination(
    destination: Destination, window: TravelWindow, request: RecommendationRequest
) -> tuple[int, RecommendationScoreBreakdown, list[str], list[str], DestinationSignals]:
    raw_signals = get_destination_signals(destination, window)
    signals = _signals_from_value(raw_signals)
    climate_score = _climate_score(signals.climate)
    attraction_score = _attraction_score(signals.attractions, destination)
    popularity_score = _popularity_score(signals.summary, destination)
    affordability_score = _affordability_score(signals.cost_of_living, destination)

    if request.preferences.climate == "warm" and signals.climate.average_temperature_c is not None:
        if signals.climate.average_temperature_c >= 18:
            climate_score = min(35, climate_score + 3)
        elif signals.climate.average_temperature_c < 12:
            climate_score = max(0, climate_score - 3)

    if request.preferences.popularity == "underrated" and "popular" in destination.tags:
        popularity_score = max(0, popularity_score - 4)
    if request.preferences.popularity == "popular" and "popular" in destination.tags:
        popularity_score = min(20, popularity_score + 3)

    if request.preferences.budget_sensitivity >= 4:
        affordability_score = min(20, affordability_score + max(0, 5 - destination.cost_level))

    breakdown = RecommendationScoreBreakdown(
        climate_score=climate_score,
        attraction_score=attraction_score,
        popularity_score=popularity_score,
        affordability_score=affordability_score,
    )
    score = (
        breakdown.climate_score
        + breakdown.attraction_score
        + breakdown.popularity_score
        + breakdown.affordability_score
    )

    reasons = [
        f"Climate fit contributes {breakdown.climate_score} points.",
        f"Live attraction density contributes {breakdown.attraction_score} points.",
        f"Popularity context contributes {breakdown.popularity_score} points.",
        f"Affordability contributes {breakdown.affordability_score} points.",
    ]

    return score, breakdown, reasons, signals.warnings, signals


def _recommendation_for(
    destination: Destination,
    window: TravelWindow,
    request: RecommendationRequest,
) -> Recommendation:
    score, breakdown, reasons, warnings, signals = score_destination(destination, window, request)
    live_caveats = [*destination.caveats]
    if warnings:
        live_caveats.append(" ".join(warnings))

    return Recommendation(
        travel_window_id=window.id,
        destination=destination,
        score=score,
        reasons=reasons,
        caveats=live_caveats,
        score_breakdown=breakdown,
        best_months_to_visit=_best_months_to_visit(destination),
        top_attractions=[attraction.name for attraction in signals.attractions[:5]],
        estimated_daily_budget=_estimated_daily_budget(signals.cost_of_living, destination),
        summary=signals.summary,
        warning=" ".join(warnings) if warnings else None,
    )


def _filtered_candidates(request: RecommendationRequest, region: str | None = None, query: str | None = None) -> list[Destination]:
    excluded = set(request.excluded_destination_ids)
    candidates = [destination for destination in load_destinations() if destination.id not in excluded]

    if region:
        region_lower = region.lower()
        candidates = [
            destination
            for destination in candidates
            if region_lower in destination.country.lower() or region_lower in destination.timezone.lower()
        ]

    if query:
        query_lower = query.lower()
        candidates = [
            destination
            for destination in candidates
            if query_lower in destination.city.lower() or query_lower in destination.country.lower()
        ]

    return candidates


def recommend_destinations(request: RecommendationRequest) -> list[RecommendationGroup]:
    candidates = _filtered_candidates(request)
    groups: list[RecommendationGroup] = []

    for window in request.travel_windows:
        ranked = [_recommendation_for(destination, window, request) for destination in candidates]
        ranked.sort(key=lambda item: item.score, reverse=True)
        groups.append(RecommendationGroup(travel_window=window, recommendations=ranked[:5]))

    return groups


def recommended_destinations_search(
    month: int | None = None,
    budget: int | None = None,
    region: str | None = None,
    query: str | None = None,
) -> list[RecommendedDestination]:
    target_month = month or date.today().month
    window = TravelWindow(
        id=f"search-{target_month}",
        start_date=date(2026, target_month, 15),
        end_date=date(2026, target_month, 18),
    )
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[window],
        preferences={"budget_sensitivity": budget or 3},
    )
    candidates = _filtered_candidates(request, region=region, query=query)
    recommendations = [_recommendation_for(destination, window, request) for destination in candidates]
    recommendations.sort(key=lambda item: item.score, reverse=True)

    return [
        RecommendedDestination(
            id=item.destination.id,
            name=item.destination.city,
            country=item.destination.country,
            coordinates=CoordinatesResult(lat=item.destination.latitude, lng=item.destination.longitude),
            travel_score=item.score,
            score_breakdown=item.score_breakdown,
            best_months_to_visit=item.best_months_to_visit,
            top_attractions=item.top_attractions,
            estimated_daily_budget=item.estimated_daily_budget,
            summary=item.summary,
            warning=item.warning,
        )
        for item in recommendations
        if item.score_breakdown is not None
    ]
