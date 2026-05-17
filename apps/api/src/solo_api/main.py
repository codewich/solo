from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
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
    return recommend_destinations(request)


@app.get("/api/destinations/recommended", response_model=list[RecommendedDestination])
def recommended_destinations(
    month: int | None = None,
    budget: int | None = None,
    region: str | None = None,
    q: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radiusKm: int = 1800,
    minPopulation: int = 250000,
) -> list[RecommendedDestination]:
    return recommended_destinations_search(
        month=month,
        budget=budget,
        region=region,
        query=q,
        latitude=latitude,
        longitude=longitude,
        radius_km=radiusKm,
        min_population=minPopulation,
    )


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
        preferences=request.preferences,
    )
