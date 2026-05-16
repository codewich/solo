from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

Pace = Literal["rushed", "balanced", "wandering"]


class TravelWindow(BaseModel):
    id: str
    start_date: date
    end_date: date
    label: str | None = None
    linked_holiday: str | None = None
    status: Literal["candidate", "planned", "archived"] = "candidate"
    notes: str | None = None

    @model_validator(mode="after")
    def ensure_valid_range(self) -> "TravelWindow":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @computed_field
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class PreferenceProfile(BaseModel):
    pace: Pace = "balanced"
    climate: Literal["cool", "mild", "warm", "any"] = "any"
    budget_sensitivity: int = Field(default=3, ge=1, le=5)
    popularity: Literal["popular", "underrated", "mix"] = "mix"
    interests: dict[str, int] = Field(
        default_factory=lambda: {
            "food": 3,
            "history": 3,
            "museums": 3,
            "nightlife": 2,
            "nature": 2,
            "architecture": 3,
        }
    )


class Destination(BaseModel):
    id: str
    city: str
    country: str
    timezone: str | None = None
    latitude: float
    longitude: float
    population: int | None = None
    region: str | None = None
    country_code: str | None = None


class RecommendationScoreBreakdown(BaseModel):
    climate_score: int = Field(alias="climateScore")
    attraction_score: int = Field(alias="attractionScore")
    popularity_score: int = Field(alias="popularityScore")
    affordability_score: int = Field(alias="affordabilityScore")

    model_config = ConfigDict(populate_by_name=True)


class RecommendationRequest(BaseModel):
    home_city: str
    center_latitude: float | None = None
    center_longitude: float | None = None
    radius_km: int = Field(default=1800, ge=1, le=5000)
    min_population: int = Field(default=250000, ge=0)
    candidate_limit: int = Field(default=12, ge=1, le=50)
    region: str | None = None
    q: str | None = None
    travel_windows: list[TravelWindow]
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)
    excluded_destination_ids: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    travel_window_id: str
    destination: Destination
    score: int
    reasons: list[str]
    caveats: list[str]
    score_breakdown: RecommendationScoreBreakdown | None = None
    best_months_to_visit: list[str] = Field(default_factory=list)
    top_attractions: list[str] = Field(default_factory=list)
    estimated_daily_budget: float | None = None
    summary: str | None = None
    warning: str | None = None


class RecommendationGroup(BaseModel):
    travel_window: TravelWindow
    recommendations: list[Recommendation]


class CoordinatesResult(BaseModel):
    lat: float
    lng: float


class RecommendedDestination(BaseModel):
    id: str
    name: str
    country: str
    coordinates: CoordinatesResult
    travel_score: int = Field(alias="travelScore")
    score_breakdown: RecommendationScoreBreakdown = Field(alias="scoreBreakdown")
    best_months_to_visit: list[str] = Field(alias="bestMonthsToVisit")
    top_attractions: list[str] = Field(alias="topAttractions")
    estimated_daily_budget: float | None = Field(default=None, alias="estimatedDailyBudget")
    summary: str | None = None
    warning: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class CitySuggestion(BaseModel):
    id: str
    name: str
    country: str
    admin1: str | None = None
    latitude: float
    longitude: float
    timezone: str | None = None


class DestinationIntelligenceRequest(BaseModel):
    destination_city: str
    country: str
    latitude: float
    longitude: float
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def ensure_valid_dates(self) -> "DestinationIntelligenceRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ClimateSummary(BaseModel):
    average_temperature_c: float | None
    precipitation_mm: float | None
    sunshine_hours: float | None
    summary: str
    source: str = "Open-Meteo"


class AttractionSummary(BaseModel):
    name: str
    category: str
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None
    source: str


class HotelPriceSummary(BaseModel):
    average_nightly_price: float | None
    median_nightly_price: float | None
    currency: str | None
    sample_size: int
    source: str = "Amadeus"
    status: Literal["available", "unavailable"] = "available"


class CostOfLivingSummary(BaseModel):
    currency: str
    meal_inexpensive: float | None = None
    coffee: float | None = None
    local_transport_ticket: float | None = None
    summary: str
    source: str


class DestinationIntelligenceWarning(BaseModel):
    step: str
    service: str
    message: str


class DestinationIntelligence(BaseModel):
    destination_city: str
    country: str
    climate: ClimateSummary
    attractions: list[AttractionSummary]
    hotels: HotelPriceSummary
    cost_of_living: CostOfLivingSummary
    warnings: list[DestinationIntelligenceWarning] = []
