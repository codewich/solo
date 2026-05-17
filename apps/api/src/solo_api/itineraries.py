from pydantic import BaseModel

from solo_api.models import TravelWindow


class ItineraryRequest(BaseModel):
    destination_city: str
    travel_window: TravelWindow


def build_itinerary(destination_city: str, window: TravelWindow) -> dict:
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
            }
        )

    return {
        "destination_city": destination_city,
        "travel_window_id": window.id,
        "days": days,
    }
