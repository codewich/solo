from pydantic import BaseModel, Field

from solo_api.models import PreferenceProfile, TravelWindow


class ItineraryRequest(BaseModel):
    destination_city: str
    travel_window: TravelWindow
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)


def build_itinerary(
    destination_city: str, window: TravelWindow, preferences: PreferenceProfile
) -> dict:
    intensity = {
        "rushed": "Add one extra optional stop if energy is high.",
        "balanced": "Keep a comfortable rhythm with time for meals and transit.",
        "wandering": "Leave generous unscheduled time for neighborhoods and cafes.",
    }[preferences.pace]

    days = []
    for index in range(window.duration_days):
        day_number = index + 1
        days.append(
            {
                "day": day_number,
                "title": f"Day {day_number} in {destination_city}",
                "morning": f"Start with a central neighborhood walk in {destination_city}.",
                "afternoon": "Choose one anchor museum, market, viewpoint, or historic area.",
                "evening": "Pick a relaxed dinner area and keep the route walkable.",
                "pace_note": intensity,
            }
        )

    return {
        "destination_city": destination_city,
        "travel_window_id": window.id,
        "pace": preferences.pace,
        "days": days,
    }
