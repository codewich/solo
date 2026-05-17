from datetime import date
from typing import Any

from solo_api.city_candidates import search_city_candidates
from solo_api.models import (
    AirQualitySummary,
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
from solo_api.recommendation_signals import DestinationSignals, dominant_month, get_destination_signals
from solo_api.storage import store_climate_normal, store_recommendation_score

DEFAULT_CENTER_LATITUDE = 51.5072
DEFAULT_CENTER_LONGITUDE = -0.1276


def _signals_from_value(value: DestinationSignals | dict[str, Any]) -> DestinationSignals:
    if isinstance(value, DestinationSignals):
        return value

    return DestinationSignals(
        climate=value["climate"],
        attraction_count=value.get("attraction_count", len(value.get("attractions", []))),
        summary=value.get("summary"),
        image_url=value.get("image_url"),
        air_quality=value.get(
            "air_quality",
            AirQualitySummary(
                pm25=None,
                pm10=None,
                no2=None,
                summary="Air quality data is unavailable; ranking used a neutral fallback.",
                status="unavailable",
            ),
        ),
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


def _attraction_score(attraction_count: int, destination: Destination) -> int:
    score = min(25, attraction_count * 4)
    if attraction_count == 0:
        score = 6
    return score


def _popularity_score(summary: str | None, destination: Destination) -> int:
    score = 0
    if summary:
        score += min(15, max(5, len(summary) // 80))
    if destination.population is not None:
        if destination.population >= 1_000_000:
            score += 5
        elif destination.population >= 500_000:
            score += 3
        elif destination.population >= 250_000:
            score += 1
    return min(20, score)


def _affordability_score(cost: CostOfLivingSummary, destination: Destination) -> int:
    if cost.status == "unavailable":
        return 10
    score = 10
    if cost.meal_inexpensive is not None:
        if cost.meal_inexpensive <= 12:
            score += 4
        elif cost.meal_inexpensive >= 22:
            score -= 4
    return max(0, min(20, score))


def _air_quality_score(air_quality: AirQualitySummary) -> int:
    if air_quality.status == "unavailable":
        return 6
    pm25 = air_quality.pm25
    if pm25 is None:
        return 6
    if pm25 <= 10:
        return 10
    if pm25 <= 15:
        return 8
    if pm25 <= 25:
        return 5
    return 2


def _best_months_to_visit(destination: Destination) -> list[str]:
    return []


def score_destination(
    destination: Destination, window: TravelWindow, request: RecommendationRequest
) -> tuple[int, RecommendationScoreBreakdown, list[str], list[str], DestinationSignals]:
    raw_signals = get_destination_signals(destination, window)
    signals = _signals_from_value(raw_signals)
    climate_score = _climate_score(signals.climate)
    attraction_score = _attraction_score(signals.attraction_count, destination)
    popularity_score = _popularity_score(signals.summary, destination)
    affordability_score = _affordability_score(signals.cost_of_living, destination)
    air_quality_score = _air_quality_score(signals.air_quality)

    breakdown = RecommendationScoreBreakdown(
        climate_score=climate_score,
        attraction_score=attraction_score,
        popularity_score=popularity_score,
        affordability_score=affordability_score,
        air_quality_score=air_quality_score,
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
        "Air quality is shown as context and is not part of the travel score.",
    ]

    return score, breakdown, reasons, signals.warnings, signals


def _recommendation_for(
    destination: Destination,
    window: TravelWindow,
    request: RecommendationRequest,
) -> Recommendation:
    score, breakdown, reasons, warnings, signals = score_destination(destination, window, request)
    store_climate_normal(
        city_id=destination.id,
        month=dominant_month(window),
        climate=signals.climate,
        source=signals.climate.source,
    )
    store_recommendation_score(
        city_id=destination.id,
        travel_window_id=window.id,
        breakdown=breakdown,
        final_score=score,
    )

    return Recommendation(
        travel_window_id=window.id,
        destination=destination,
        score=score,
        reasons=reasons,
        caveats=[" ".join(warnings)] if warnings else [],
        score_breakdown=breakdown,
        best_months_to_visit=_best_months_to_visit(destination),
        top_attractions=[],
        attraction_count=signals.attraction_count,
        summary=signals.summary,
        image_url=signals.image_url,
        climate=signals.climate,
        air_quality=signals.air_quality,
        warning=" ".join(warnings) if warnings else None,
    )


def _filtered_candidates(
    request: RecommendationRequest,
    region: str | None = None,
    query: str | None = None,
) -> list[Destination]:
    excluded = set(request.excluded_destination_ids)
    return [
        destination
        for destination in search_city_candidates(
            latitude=request.center_latitude or DEFAULT_CENTER_LATITUDE,
            longitude=request.center_longitude or DEFAULT_CENTER_LONGITUDE,
            radius_km=request.radius_km,
            min_population=request.min_population,
            limit=request.candidate_limit,
            region=region or request.region,
            query=query or request.q,
        )
        if destination.id not in excluded
    ]


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
    region: str | None = None,
    query: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: int = 1800,
    min_population: int = 250000,
) -> list[RecommendedDestination]:
    target_month = month or date.today().month
    window = TravelWindow(
        id=f"search-{target_month}",
        start_date=date(2026, target_month, 15),
        end_date=date(2026, target_month, 18),
    )
    request = RecommendationRequest(
        home_city="London",
        center_latitude=latitude or DEFAULT_CENTER_LATITUDE,
        center_longitude=longitude or DEFAULT_CENTER_LONGITUDE,
        radius_km=radius_km,
        min_population=min_population,
        travel_windows=[window],
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
            attraction_count=item.attraction_count,
            summary=item.summary,
            image_url=item.image_url,
            air_quality=item.air_quality,
            warning=item.warning,
        )
        for item in recommendations
        if item.score_breakdown is not None
    ]
