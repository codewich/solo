from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

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
    timezone: str
    latitude: float
    longitude: float
    cost_level: int = Field(ge=1, le=5)
    short_stay_score: int = Field(ge=1, le=5)
    solo_friendliness: int = Field(ge=1, le=5)
    tags: list[str]
    seasonal_strengths: dict[str, list[str]]
    climate_notes: str
    caveats: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    home_city: str
    travel_windows: list[TravelWindow]
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)
    excluded_destination_ids: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    travel_window_id: str
    destination: Destination
    score: int
    reasons: list[str]
    caveats: list[str]


class RecommendationGroup(BaseModel):
    travel_window: TravelWindow
    recommendations: list[Recommendation]
