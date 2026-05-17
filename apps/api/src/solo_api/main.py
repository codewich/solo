from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from solo_api.city_candidates import CityCatalogNotReadyError
from solo_api.config import get_env
from solo_api.destination_intelligence import (
    DestinationIntelligenceStepError,
    build_destination_intelligence,
)
from solo_api.geocoding import search_cities
from solo_api.holidays import get_bank_holidays
from solo_api.itineraries import ItineraryRequest, build_itinerary
from solo_api.models import (
    CitySuggestion,
    DestinationIntelligence,
    DestinationIntelligenceRequest,
    RecommendedDestination,
    RecommendationGroup,
    RecommendationRequest,
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


@app.get("/holidays")
def holidays(country: str = "GB", year: int = 2026) -> list[dict[str, str]]:
    return get_bank_holidays(country=country, year=year)


@app.get("/geocode/cities")
def geocode_cities(query: str, count: int = 5) -> list[CitySuggestion]:
    return search_cities(query=query, count=count)


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
