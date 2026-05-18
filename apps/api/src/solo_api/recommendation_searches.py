from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from solo_api.city_candidates import search_city_candidates
from solo_api.models import (
    Destination,
    DestinationIntelligence,
    DestinationIntelligenceRequest,
    Recommendation,
    RecommendationSearchCity,
    RecommendationSearchCreateRequest,
    RecommendationSearchCreateResponse,
    TravelWindow,
    TravelWindowDeleteRequest,
)
from solo_api.recommendations import DEFAULT_CENTER_LATITUDE, DEFAULT_CENTER_LONGITUDE, _recommendation_for
from solo_api.storage import (
    create_or_replace_recommendation_search,
    delete_travel_window,
    ensure_user,
    get_city,
    get_recommendation_search,
    get_saved_recommendation_results,
    get_user_id_for_auth,
    store_recommendation_result,
)
from solo_api.destination_intelligence import build_destination_intelligence


@dataclass
class MemorySearch:
    id: str
    travel_window: TravelWindow
    home_city: Destination
    radius_km: int
    min_population: int
    candidate_limit: int
    excluded_city_ids: list[str]


MEMORY_SEARCHES: dict[str, MemorySearch] = {}


def create_recommendation_search(
    request: RecommendationSearchCreateRequest,
) -> RecommendationSearchCreateResponse:
    user_id = ensure_user(
        email=request.user_email,
        name=request.user_name,
        provider_subject=request.provider_subject,
    )
    home_city = get_city(request.home_city_id)
    if home_city is None:
        raise ValueError("Selected home city was not found in the city catalog.")

    search_id = create_or_replace_recommendation_search(
        user_id=user_id,
        travel_window=request.travel_window,
        home_city_id=request.home_city_id,
        radius_km=request.radius_km,
        min_population=request.min_population,
        candidate_limit=request.candidate_limit,
        excluded_city_ids=request.excluded_city_ids,
    )
    MEMORY_SEARCHES[search_id] = MemorySearch(
        id=search_id,
        travel_window=request.travel_window,
        home_city=home_city,
        radius_km=request.radius_km,
        min_population=request.min_population,
        candidate_limit=request.candidate_limit,
        excluded_city_ids=request.excluded_city_ids,
    )
    return RecommendationSearchCreateResponse(id=search_id, travel_window_id=request.travel_window.id)


def _search_from_storage(search_id: str) -> MemorySearch | None:
    if search_id in MEMORY_SEARCHES:
        return MEMORY_SEARCHES[search_id]

    row = get_recommendation_search(search_id)
    if row is None:
        return None
    home_city = get_city(row["home_city_id"])
    if home_city is None:
        return None
    search = MemorySearch(
        id=str(row["id"]),
        travel_window=TravelWindow(
            id=str(row["travel_window_id"]),
            label=row["label"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            status=row["status"],
        ),
        home_city=home_city,
        radius_km=row["radius_km"],
        min_population=row["min_population"],
        candidate_limit=row["candidate_limit"],
        excluded_city_ids=list(row.get("excluded_city_ids") or []),
    )
    MEMORY_SEARCHES[search_id] = search
    return search


def get_search_or_error(search_id: str) -> MemorySearch:
    search = _search_from_storage(search_id)
    if search is None:
        raise ValueError("Recommendation search was not found.")
    return search


def list_recommendation_search_cities(search_id: str) -> list[RecommendationSearchCity]:
    search = get_search_or_error(search_id)
    excluded = set(search.excluded_city_ids)
    excluded.add(search.home_city.id)
    destinations = search_city_candidates(
        latitude=search.home_city.latitude or DEFAULT_CENTER_LATITUDE,
        longitude=search.home_city.longitude or DEFAULT_CENTER_LONGITUDE,
        radius_km=search.radius_km,
        min_population=search.min_population,
        limit=search.candidate_limit,
    )
    return [
        RecommendationSearchCity(search_id=search_id, destination=destination)
        for destination in destinations
        if destination.id not in excluded
    ][: search.candidate_limit]


def score_recommendation_search_city(search_id: str, city_id: str) -> Recommendation:
    search = get_search_or_error(search_id)
    destination = get_city(city_id)
    if destination is None:
        raise ValueError("Candidate city was not found in the city catalog.")
    recommendation = _recommendation_for(destination, search.travel_window, _request_like(search))
    store_recommendation_result(search_id=search_id, recommendation=recommendation)
    return recommendation


def load_recommendation_search_city_intelligence(
    search_id: str,
    city_id: str,
) -> DestinationIntelligence:
    search = get_search_or_error(search_id)
    destination = get_city(city_id)
    if destination is None:
        raise ValueError("Candidate city was not found in the city catalog.")
    return build_destination_intelligence(
        DestinationIntelligenceRequest(
            city_id=destination.id,
            destination_city=destination.city,
            country=destination.country,
            latitude=destination.latitude,
            longitude=destination.longitude,
            start_date=search.travel_window.start_date,
            end_date=search.travel_window.end_date,
        )
    )


def saved_recommendation_search_results(search_id: str) -> list[Recommendation]:
    return get_saved_recommendation_results(search_id)


def remove_travel_window(window_id: str, request: TravelWindowDeleteRequest) -> None:
    user_id = get_user_id_for_auth(
        email=request.user_email,
        provider_subject=request.provider_subject,
    )
    if user_id is None:
        raise ValueError("Signed-in user was not found.")
    if not delete_travel_window(user_id=user_id, travel_window_id=window_id):
        raise ValueError("Travel window was not found.")


def _request_like(search: MemorySearch) -> Any:
    return type(
        "RecommendationSearchRequest",
        (),
        {
            "excluded_destination_ids": search.excluded_city_ids,
            "radius_km": search.radius_km,
            "min_population": search.min_population,
            "candidate_limit": search.candidate_limit,
            "region": None,
            "q": None,
            "center_latitude": search.home_city.latitude,
            "center_longitude": search.home_city.longitude,
        },
    )()
