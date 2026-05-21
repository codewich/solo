from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

SearchMode = Literal["radius", "rectangle"]


class SearchBounds(BaseModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def ensure_normal_bounds(self) -> "SearchBounds":
        if self.west >= self.east:
            raise ValueError("west must be less than east")
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        return self


class RecommendationSearchSummary(BaseModel):
    id: str
    home_city_id: str
    home_city: "Destination | None" = None
    radius_km: int
    min_population: int
    candidate_limit: int
    search_mode: SearchMode = "radius"
    search_bounds: SearchBounds | None = None
    result_count: int = 0


class TravelWindow(BaseModel):
    id: str
    start_date: date
    end_date: date
    label: str | None = None
    status: Literal["candidate", "planned", "archived"] = "candidate"
    latest_search: RecommendationSearchSummary | None = None

    @model_validator(mode="after")
    def ensure_valid_range(self) -> "TravelWindow":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @computed_field
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


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
    air_quality_score: int = Field(default=6, alias="airQualityScore")

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
    attraction_count: int = Field(default=0, alias="attractionCount")
    summary: str | None = None
    image_url: str | None = Field(default=None, alias="imageUrl")
    climate: "ClimateSummary | None" = None
    air_quality: "AirQualitySummary | None" = Field(default=None, alias="airQuality")
    warning: str | None = None
    status: Literal["ready", "error"] = "ready"

    model_config = ConfigDict(populate_by_name=True)


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
    attraction_count: int = Field(default=0, alias="attractionCount")
    summary: str | None = None
    image_url: str | None = Field(default=None, alias="imageUrl")
    climate: "ClimateSummary | None" = None
    air_quality: "AirQualitySummary | None" = Field(default=None, alias="airQuality")
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
    country_code: str | None = None


class HolidayRegion(BaseModel):
    country_code: str
    region_code: str
    name: str


class PublicHoliday(BaseModel):
    date: date
    name: str
    country_code: str
    region_code: str | None = None
    type: str | None = None


class DestinationIntelligenceRequest(BaseModel):
    city_id: str | None = None
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
    average_temperature_min_c: float | None = None
    average_temperature_max_c: float | None = None
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


class AirQualitySummary(BaseModel):
    european_aqi: float | None = None
    us_aqi: float | None = None
    pm25: float | None = None
    pm10: float | None = None
    no2: float | None = None
    summary: str
    source: str = "Open-Meteo"
    status: Literal["available", "unavailable"] = "available"


class DestinationIntelligenceWarning(BaseModel):
    step: str
    service: str
    message: str


class DestinationIntelligence(BaseModel):
    destination_city: str
    country: str
    climate: ClimateSummary
    attractions: list[AttractionSummary]
    warnings: list[DestinationIntelligenceWarning] = []


class RecommendationSearchCreateRequest(BaseModel):
    travel_window: TravelWindow
    home_city_id: str
    radius_km: int = Field(default=1800, ge=1, le=5000)
    search_mode: SearchMode = "radius"
    search_bounds: SearchBounds | None = None
    min_population: int = Field(default=250000, ge=0)
    candidate_limit: int = Field(default=10, ge=1, le=50)
    excluded_city_ids: list[str] = Field(default_factory=list)
    user_email: str | None = None
    user_name: str | None = None
    provider_subject: str | None = None

    @model_validator(mode="after")
    def ensure_search_mode_shape(self) -> "RecommendationSearchCreateRequest":
        if self.search_mode == "rectangle" and self.search_bounds is None:
            raise ValueError("search_bounds is required for rectangle search")
        if self.search_mode == "radius":
            self.search_bounds = None
        return self


class TravelWindowDeleteRequest(BaseModel):
    user_email: str
    provider_subject: str | None = None


class RecommendationSearchCreateResponse(BaseModel):
    id: str
    travel_window_id: str
    status: Literal["created"] = "created"


class RecommendationSearchCity(BaseModel):
    search_id: str
    destination: Destination


class NearestCityRequest(BaseModel):
    latitude: float
    longitude: float
