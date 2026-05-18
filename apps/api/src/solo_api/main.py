import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from solo_api.city_candidates import CityCatalogNotReadyError
from solo_api.config import get_env

# Configure logging
log_level = get_env("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
from solo_api.destination_intelligence import (
    DestinationIntelligenceStepError,
    build_destination_intelligence,
)
from solo_api.geocoding import search_cities
from solo_api.geocoding import nearest_city as find_nearest_city_suggestion
from solo_api.holidays import CalendarificProviderError, get_bank_holidays, get_holiday_regions
from solo_api.itineraries import ItineraryRequest, build_itinerary
from solo_api.models import (
    CitySuggestion,
    DestinationIntelligence,
    DestinationIntelligenceRequest,
    HolidayRegion,
    NearestCityRequest,
    PublicHoliday,
    RecommendedDestination,
    RecommendationGroup,
    RecommendationRequest,
    Recommendation,
    RecommendationSearchCity,
    RecommendationSearchCreateRequest,
    RecommendationSearchCreateResponse,
    TravelWindow,
    TravelWindowDeleteRequest,
)
from solo_api.recommendation_searches import (
    create_recommendation_search,
    list_recommendation_search_cities,
    load_recommendation_search_city_intelligence,
    remove_travel_window,
    saved_recommendation_search_results,
    saved_travel_windows,
    score_recommendation_search_city,
)
from solo_api.recommendations import recommend_destinations, recommended_destinations_search

app = FastAPI(title="Solo API", version="0.1.0")


def _cors_origins() -> list[str]:
    configured = get_env("CORS_ALLOWED_ORIGINS")
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://solo-web-beryl.vercel.app",
    ]
    if configured:
        origins.extend(origin.strip() for origin in configured.split(",") if origin.strip())
    nextauth_url = get_env("NEXTAUTH_URL")
    if nextauth_url:
        origins.append(nextauth_url.rstrip("/"))
    return list(dict.fromkeys(origins))


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=get_env("CORS_ALLOWED_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "solo-api"}


@app.get("/holidays/regions")
def holiday_regions(country: str) -> list[HolidayRegion]:
    try:
        return get_holiday_regions(country=country)
    except CalendarificProviderError as error:
        raise HTTPException(status_code=502, detail={"message": str(error)}) from error


@app.get("/holidays")
def holidays(country: str = "GB", year: int = 2026, region: str | None = None) -> list[PublicHoliday]:
    try:
        return get_bank_holidays(country=country, year=year, region=region)
    except CalendarificProviderError as error:
        raise HTTPException(status_code=502, detail={"message": str(error)}) from error


@app.get("/geocode/cities")
def geocode_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    return search_cities(query=query, count=count)


@app.post("/geocode/nearest-city")
def geocode_nearest_city(request: NearestCityRequest) -> CitySuggestion:
    suggestion = find_nearest_city_suggestion(
        latitude=request.latitude,
        longitude=request.longitude,
    )
    if suggestion is None:
        raise HTTPException(status_code=404, detail={"message": "No city catalog match found."})
    return suggestion


@app.post("/recommendation-searches")
def recommendation_searches(
    request: RecommendationSearchCreateRequest,
) -> RecommendationSearchCreateResponse:
    try:
        return create_recommendation_search(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"message": str(error)}) from error


@app.get("/travel-windows")
def list_saved_travel_windows(
    user_email: str,
    provider_subject: str | None = None,
) -> list[TravelWindow]:
    return saved_travel_windows(
        user_email=user_email,
        provider_subject=provider_subject,
    )


@app.delete("/travel-windows/{window_id}", status_code=204)
def delete_saved_travel_window(window_id: str, request: TravelWindowDeleteRequest) -> None:
    try:
        remove_travel_window(window_id, request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail={"message": str(error)}) from error


@app.get("/recommendation-searches/{search_id}/cities")
def recommendation_search_cities(search_id: str) -> list[RecommendationSearchCity]:
    try:
        return list_recommendation_search_cities(search_id)
    except CityCatalogNotReadyError as error:
        raise HTTPException(status_code=503, detail={"message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail={"message": str(error)}) from error


@app.get("/recommendation-searches/{search_id}/recommendations")
def recommendation_search_results(search_id: str) -> list[Recommendation]:
    return saved_recommendation_search_results(search_id)


@app.post("/recommendation-searches/{search_id}/cities/{city_id}/score")
def recommendation_search_city_score(search_id: str, city_id: str) -> Recommendation:
    try:
        return score_recommendation_search_city(search_id, city_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail={"message": str(error)}) from error


@app.post("/recommendation-searches/{search_id}/cities/{city_id}/intelligence")
def recommendation_search_city_intelligence(
    search_id: str,
    city_id: str,
) -> DestinationIntelligence:
    try:
        return load_recommendation_search_city_intelligence(search_id, city_id)
    except DestinationIntelligenceStepError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "step": error.step,
                "service": error.service,
                "message": error.message,
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=404, detail={"message": str(error)}) from error


@app.post("/recommendations")
def recommendations(request: RecommendationRequest) -> list[RecommendationGroup]:
    try:
        return recommend_destinations(request)
    except CityCatalogNotReadyError as error:
        raise HTTPException(status_code=503, detail={"message": str(error)}) from error


@app.get("/api/destinations/recommended", response_model=list[RecommendedDestination])
def recommended_destinations(
    month: int | None = None,
    region: str | None = None,
    q: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radiusKm: int = 1800,
    minPopulation: int = 250000,
) -> list[RecommendedDestination]:
    try:
        return recommended_destinations_search(
            month=month,
            region=region,
            query=q,
            latitude=latitude,
            longitude=longitude,
            radius_km=radiusKm,
            min_population=minPopulation,
        )
    except CityCatalogNotReadyError as error:
        raise HTTPException(status_code=503, detail={"message": str(error)}) from error


@app.post("/destination-intelligence")
def destination_intelligence(
    request: DestinationIntelligenceRequest,
) -> DestinationIntelligence:
    try:
        return build_destination_intelligence(request)
    except DestinationIntelligenceStepError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "step": error.step,
                "service": error.service,
                "message": error.message,
            },
        ) from error


@app.post("/itineraries")
def itineraries(request: ItineraryRequest) -> dict:
    return build_itinerary(
        destination_city=request.destination_city,
        window=request.travel_window,
    )
