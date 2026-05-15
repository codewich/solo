from datetime import date

from fastapi.testclient import TestClient

from solo_api.itineraries import build_itinerary
from solo_api.models import PreferenceProfile, TravelWindow


def test_itinerary_matches_window_duration():
    window = TravelWindow(
        id="long-weekend", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)
    )

    itinerary = build_itinerary(
        destination_city="Lisbon", window=window, preferences=PreferenceProfile(pace="wandering")
    )

    assert len(itinerary["days"]) == 3
    assert itinerary["pace"] == "wandering"


def test_itinerary_endpoint_returns_days():
    client = TestClient(__import__("solo_api.main", fromlist=["app"]).app)

    response = client.post(
        "/itineraries",
        json={
            "destination_city": "Porto",
            "travel_window": {
                "id": "porto-trip",
                "start_date": "2026-06-12",
                "end_date": "2026-06-15",
            },
            "preferences": {"pace": "balanced"},
        },
    )

    assert response.status_code == 200
    assert len(response.json()["days"]) == 4
