from datetime import date

from fastapi.testclient import TestClient

from solo_api.main import app
from solo_api.models import (
    AttractionSummary,
    ClimateSummary,
    CostOfLivingSummary,
    PreferenceProfile,
    RecommendationRequest,
    TravelWindow,
)
from solo_api.recommendations import recommend_destinations
from solo_api.recommendation_signals import SIGNAL_CACHE, get_destination_signals


def city(id: str = "lisbon-pt", name: str = "Lisbon"):
    from solo_api.models import Destination

    return Destination(
        id=id,
        city=name,
        country="Portugal",
        country_code="PT",
        latitude=38.7223,
        longitude=-9.1393,
        population=544851,
        timezone="Europe/Lisbon",
    )


def stub_live_signals(monkeypatch):
    def fake_signals(destination, window):
        return {
            "climate": ClimateSummary(
                average_temperature_c=22,
                precipitation_mm=4,
                sunshine_hours=7,
                summary="Stubbed climate.",
            ),
            "attractions": [
                AttractionSummary(name="Museum", category="museum", source="OpenStreetMap"),
                AttractionSummary(name="Viewpoint", category="viewpoint", source="OpenStreetMap"),
            ],
            "summary": f"{destination.city} has a useful travel summary.",
            "cost_of_living": CostOfLivingSummary(
                currency="EUR",
                meal_inexpensive=14,
                coffee=2,
                local_transport_ticket=2,
                summary="Stubbed costs.",
                source="Static Numbeo-compatible seed",
            ),
            "warnings": [],
        }

    monkeypatch.setattr("solo_api.recommendations.get_destination_signals", fake_signals)


def stub_city_candidates(monkeypatch):
    monkeypatch.setattr(
        "solo_api.recommendations.search_city_candidates",
        lambda **kwargs: [
            city("lisbon-pt", "Lisbon"),
            city("porto-pt", "Porto"),
            city("prague-cz", "Prague"),
        ],
    )


def test_recommendations_are_grouped_by_travel_window(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
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


def test_recommendations_respect_exclusions(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
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


def test_recommendations_endpoint_returns_groups(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
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


def test_recommendations_include_live_score_breakdown(monkeypatch):
    def fake_signals(destination, window):
        return {
            "climate": ClimateSummary(
                average_temperature_c=23,
                precipitation_mm=2,
                sunshine_hours=8,
                summary="Mild and bright.",
            ),
            "attractions": [
                AttractionSummary(name=f"Attraction {index}", category="museum", source="OpenStreetMap")
                for index in range(6)
            ],
            "summary": "A well documented city with strong cultural presence.",
            "cost_of_living": CostOfLivingSummary(
                currency="EUR",
                meal_inexpensive=12,
                coffee=2,
                local_transport_ticket=2,
                summary="Moderate daily costs.",
                source="Static Numbeo-compatible seed",
            ),
            "warnings": [],
        }

    monkeypatch.setattr("solo_api.recommendations.get_destination_signals", fake_signals)
    stub_city_candidates(monkeypatch)
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))
        ],
        preferences=PreferenceProfile(climate="warm", budget_sensitivity=4),
    )

    groups = recommend_destinations(request)
    first = groups[0].recommendations[0]

    assert first.score_breakdown is not None
    assert first.score == (
        first.score_breakdown.climate_score
        + first.score_breakdown.attraction_score
        + first.score_breakdown.popularity_score
        + first.score_breakdown.affordability_score
    )
    assert first.top_attractions[:2] == ["Attraction 0", "Attraction 1"]
    assert first.summary == "A well documented city with strong cultural presence."


def test_destination_signals_are_cached(monkeypatch):
    SIGNAL_CACHE._values.clear()
    calls = {"climate": 0, "attractions": 0, "summary": 0}

    def fake_climate(**kwargs):
        calls["climate"] += 1
        return ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Cached climate.",
        )

    def fake_attractions(**kwargs):
        calls["attractions"] += 1
        return [AttractionSummary(name="Museum", category="museum", source="OpenStreetMap")]

    def fake_summary(city):
        calls["summary"] += 1
        return f"{city} summary"

    monkeypatch.setattr("solo_api.recommendation_signals.fetch_climate_summary", fake_climate)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_attractions", fake_attractions)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", fake_summary)

    destination = city()
    window = TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    first = get_destination_signals(destination, window)
    second = get_destination_signals(destination, window)

    assert first == second
    assert calls == {"climate": 1, "attractions": 1, "summary": 1}


def test_destination_signals_fall_back_with_warning(monkeypatch):
    SIGNAL_CACHE._values.clear()

    def broken_climate(**kwargs):
        raise RuntimeError("weather down")

    monkeypatch.setattr("solo_api.recommendation_signals.fetch_climate_summary", broken_climate)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_attractions", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)

    destination = city()
    signals = get_destination_signals(
        destination,
        TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
    )

    assert signals.climate.average_temperature_c is None
    assert any("Open-Meteo unavailable" in warning for warning in signals.warnings)
    assert any("Wikimedia unavailable" in warning for warning in signals.warnings)


def test_recommended_destinations_endpoint_returns_direct_search_shape(monkeypatch):
    def fake_signals(destination, window):
        return {
            "climate": ClimateSummary(
                average_temperature_c=24,
                precipitation_mm=3,
                sunshine_hours=9,
                summary="Warm and suitable.",
            ),
            "attractions": [
                AttractionSummary(name="Central Museum", category="museum", source="OpenStreetMap")
            ],
            "summary": f"{destination.city} summary.",
            "cost_of_living": CostOfLivingSummary(
                currency="EUR",
                meal_inexpensive=11,
                coffee=2,
                local_transport_ticket=2,
                summary="Affordable.",
                source="Static Numbeo-compatible seed",
            ),
            "warnings": [],
        }

    monkeypatch.setattr("solo_api.recommendations.get_destination_signals", fake_signals)
    stub_city_candidates(monkeypatch)
    client = TestClient(app)

    response = client.get(
        "/api/destinations/recommended?month=5&budget=4&region=PT&q=lis&radiusKm=1200&minPopulation=300000"
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == "lisbon-pt"
    assert body[0]["name"] == "Lisbon"
    assert body[0]["coordinates"] == {"lat": 38.7223, "lng": -9.1393}
    assert body[0]["travelScore"] == sum(body[0]["scoreBreakdown"].values())
    assert body[0]["topAttractions"] == ["Central Museum"]


def test_recommendations_query_city_candidates_with_radius_and_population(monkeypatch):
    stub_live_signals(monkeypatch)
    calls = []

    def fake_search_city_candidates(**kwargs):
        calls.append(kwargs)
        return [city()]

    monkeypatch.setattr("solo_api.recommendations.search_city_candidates", fake_search_city_candidates)
    request = RecommendationRequest(
        home_city="London",
        center_latitude=51.5072,
        center_longitude=-0.1276,
        radius_km=900,
        min_population=500000,
        candidate_limit=7,
        region="PT",
        q="Lis",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))
        ],
    )

    recommend_destinations(request)

    assert calls == [
        {
            "latitude": 51.5072,
            "longitude": -0.1276,
            "radius_km": 900,
            "min_population": 500000,
            "limit": 7,
            "region": "PT",
            "query": "Lis",
        }
    ]
