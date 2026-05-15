from datetime import date

from fastapi.testclient import TestClient

from solo_api.main import app
from solo_api.models import PreferenceProfile, RecommendationRequest, TravelWindow
from solo_api.recommendations import recommend_destinations


def test_recommendations_are_grouped_by_travel_window():
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
            TravelWindow(id="august", start_date=date(2026, 8, 29), end_date=date(2026, 8, 31)),
        ],
        preferences=PreferenceProfile(climate="warm", interests={"food": 5, "history": 2}),
    )

    groups = recommend_destinations(request)

    assert [group.travel_window.id for group in groups] == ["may", "august"]
    assert all(group.recommendations for group in groups)


def test_recommendations_respect_exclusions():
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))
        ],
        excluded_destination_ids=["lisbon-pt", "seville-es"],
    )

    groups = recommend_destinations(request)
    destination_ids = {item.destination.id for item in groups[0].recommendations}

    assert "lisbon-pt" not in destination_ids
    assert "seville-es" not in destination_ids


def test_recommendations_endpoint_returns_groups():
    client = TestClient(app)

    response = client.post(
        "/recommendations",
        json={
            "home_city": "London",
            "travel_windows": [
                {"id": "may", "start_date": "2026-05-23", "end_date": "2026-05-25"}
            ],
            "preferences": {"pace": "wandering", "climate": "warm", "budget_sensitivity": 3},
            "excluded_destination_ids": ["prague-cz"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["travel_window"]["id"] == "may"
    assert body[0]["recommendations"][0]["destination"]["id"] != "prague-cz"
