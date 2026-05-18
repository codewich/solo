from datetime import date

from solo_api.models import (
    AirQualitySummary,
    AttractionSummary,
    ClimateSummary,
    RecommendationRequest,
    TravelWindow,
)
from solo_api.recommendations import recommend_destinations, recommended_destinations_search
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
            "attraction_count": 2,
            "summary": f"{destination.city} has a useful travel summary.",
            "image_url": f"https://images.example/{destination.city}.jpg",
            "air_quality": AirQualitySummary(
                pm25=8.0,
                pm10=14.0,
                no2=None,
                summary="Good air quality.",
                source="Open-Meteo",
                status="available",
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
    request = RecommendationRequest(
        home_city="London",
        travel_windows=[
            TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))
        ],
        excluded_destination_ids=["prague-cz"],
    )

    groups = recommend_destinations(request)

    assert groups[0].travel_window.id == "may"
    assert groups[0].recommendations[0].destination.id != "prague-cz"


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
            "attraction_count": 6,
            "summary": "A well documented city with strong cultural presence.",
            "image_url": "https://images.example/lisbon.jpg",
            "air_quality": AirQualitySummary(
                pm25=7.0,
                pm10=12.0,
                no2=20.0,
                summary="Good air quality.",
                source="Open-Meteo",
                status="available",
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
    )

    groups = recommend_destinations(request)
    first = groups[0].recommendations[0]

    assert first.score_breakdown is not None
    assert first.score == (
        first.score_breakdown.climate_score
        + first.score_breakdown.attraction_score
        + first.score_breakdown.popularity_score
    )
    assert first.attraction_count == 6
    assert first.top_attractions == []
    assert first.summary == "A well documented city with strong cultural presence."
    assert first.image_url == "https://images.example/lisbon.jpg"
    assert first.air_quality is not None
    assert first.air_quality.status == "available"
    assert first.climate is not None
    assert first.climate.average_temperature_c == 23
    assert first.climate.summary == "Mild and bright."


def test_recommendations_store_climate_normals(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
    stored = []
    monkeypatch.setattr(
        "solo_api.recommendations.store_climate_normal",
        lambda **kwargs: stored.append(kwargs),
    )

    recommend_destinations(
        RecommendationRequest(
            home_city="London",
            travel_windows=[
                TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))
            ],
        )
    )

    assert stored
    assert stored[0]["city_id"] == "lisbon-pt"
    assert stored[0]["month"] == 5
    assert stored[0]["climate"].average_temperature_c == 22


def test_recommendations_use_later_month_when_window_month_coverage_ties(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
    stored = []
    monkeypatch.setattr(
        "solo_api.recommendations.store_climate_normal",
        lambda **kwargs: stored.append(kwargs),
    )

    recommend_destinations(
        RecommendationRequest(
            home_city="London",
            travel_windows=[
                TravelWindow(id="split", start_date=date(2026, 5, 31), end_date=date(2026, 6, 1))
            ],
        )
    )

    assert stored
    assert stored[0]["month"] == 6


def test_recommendations_use_last_calendar_month_for_december_january_tie(monkeypatch):
    stub_live_signals(monkeypatch)
    stub_city_candidates(monkeypatch)
    stored = []
    monkeypatch.setattr(
        "solo_api.recommendations.store_climate_normal",
        lambda **kwargs: stored.append(kwargs),
    )

    recommend_destinations(
        RecommendationRequest(
            home_city="London",
            travel_windows=[
                TravelWindow(id="new-year", start_date=date(2026, 12, 31), end_date=date(2027, 1, 1))
            ],
        )
    )

    assert stored
    assert stored[0]["month"] == 1


def test_destination_signals_are_cached(monkeypatch):
    SIGNAL_CACHE._values.clear()
    calls = {"climate": 0, "attractions": 0, "summary": 0, "image": 0, "air_quality": 0}

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
        return [
            AttractionSummary(name=f"Attraction {index}", category="museum", source="OpenStreetMap")
            for index in range(8)
        ]

    def fake_summary(city):
        calls["summary"] += 1
        return f"{city} summary"

    def fake_image(city):
        calls["image"] += 1
        return f"https://images.example/{city}.jpg"

    def fake_air_quality(**kwargs):
        calls["air_quality"] += 1
        return AirQualitySummary(
            pm25=9.0,
            pm10=None,
            no2=None,
            summary="Good air quality.",
            source="Open-Meteo",
            status="available",
        )

    monkeypatch.setattr("solo_api.recommendation_signals.fetch_month_climate_summary", fake_climate)
    monkeypatch.setattr("solo_api.recommendation_signals.get_climate_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.store_climate_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", fake_attractions)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", fake_summary)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", fake_image)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_air_quality_summary", fake_air_quality)

    destination = city()
    window = TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25))

    first = get_destination_signals(destination, window)
    second = get_destination_signals(destination, window)

    assert first == second
    assert calls == {"climate": 1, "attractions": 1, "summary": 1, "image": 1, "air_quality": 1}


def test_destination_signals_do_not_write_search_scoped_shared_cache(monkeypatch):
    SIGNAL_CACHE._values.clear()
    writes = []

    monkeypatch.setattr(
        "solo_api.recommendation_signals.set_api_cache",
        lambda key, payload, ttl_seconds, provider: writes.append(
            (key, payload, ttl_seconds, provider)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_month_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Cached climate.",
        ),
    )
    monkeypatch.setattr("solo_api.recommendation_signals.get_climate_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.store_climate_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.resolve_city_attractions",
        lambda **kwargs: [
            AttractionSummary(name=f"Attraction {index}", category="museum", source="OpenStreetMap")
            for index in range(8)
        ],
    )
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: AirQualitySummary(
            pm25=9.0,
            pm10=None,
            no2=None,
            summary="Good air quality.",
            source="Open-Meteo",
            status="available",
        ),
    )

    get_destination_signals(
        city(),
        TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
    )

    assert writes == []


def test_destination_signals_reads_monthly_climate_from_storage(monkeypatch):
    SIGNAL_CACHE._values.clear()
    stored_climate = ClimateSummary(
        average_temperature_c=21,
        average_temperature_min_c=16,
        average_temperature_max_c=26,
        precipitation_mm=2,
        sunshine_hours=8,
        summary="Stored monthly climate.",
    )

    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_climate_normal",
        lambda **kwargs: stored_climate,
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_month_climate_summary",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not fetch climate")),
    )
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: AirQualitySummary(
            summary="Good air quality.",
            source="Open-Meteo",
            status="available",
        ),
    )

    signals = get_destination_signals(
        city(),
        TravelWindow(id="june", start_date=date(2026, 5, 31), end_date=date(2026, 6, 2)),
    )

    assert signals.climate == stored_climate


def test_destination_signals_reads_monthly_air_quality_from_storage(monkeypatch):
    SIGNAL_CACHE._values.clear()
    stored_air_quality = AirQualitySummary(
        european_aqi=20,
        us_aqi=50,
        pm25=9,
        pm10=20,
        no2=25,
        summary="Stored air quality.",
        source="Open-Meteo",
        status="available",
    )

    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_climate_normal",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Stored climate.",
        ),
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_air_quality_normal",
        lambda **kwargs: stored_air_quality,
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("should not fetch air quality")),
    )
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)

    signals = get_destination_signals(
        city(id="2988507", name="Paris"),
        TravelWindow(id="may", start_date=date(2027, 5, 23), end_date=date(2027, 6, 4)),
    )

    assert signals.air_quality == stored_air_quality


def test_destination_signals_stores_monthly_air_quality_after_provider_fetch(monkeypatch):
    SIGNAL_CACHE._values.clear()
    fetched_air_quality = AirQualitySummary(
        european_aqi=20,
        us_aqi=50,
        pm25=9,
        pm10=20,
        no2=25,
        summary="Fetched air quality.",
        source="Open-Meteo",
        status="available",
    )
    stored = []

    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_climate_normal",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Stored climate.",
        ),
    )
    monkeypatch.setattr("solo_api.recommendation_signals.get_air_quality_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.air_quality_sample_year", lambda: 2025)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: fetched_air_quality,
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.store_air_quality_normal",
        lambda **kwargs: stored.append(kwargs),
    )
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)

    signals = get_destination_signals(
        city(id="2988507", name="Paris"),
        TravelWindow(id="may", start_date=date(2027, 5, 23), end_date=date(2027, 6, 4)),
    )

    assert signals.air_quality == fetched_air_quality
    assert stored == [
        {
            "city_id": "2988507",
            "year": 2025,
            "month": 5,
            "air_quality": fetched_air_quality,
        }
    ]


def test_destination_signals_use_resolved_city_attractions(monkeypatch):
    SIGNAL_CACHE._values.clear()
    attractions = [
        AttractionSummary(name="Museum", category="museum", source="OpenStreetMap"),
        AttractionSummary(name="Viewpoint", category="viewpoint", source="OpenStreetMap"),
    ]

    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_climate_normal",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Stored climate.",
        ),
    )
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", lambda **kwargs: attractions)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: AirQualitySummary(
            summary="Good air quality.",
            source="Open-Meteo",
            status="available",
        ),
    )

    signals = get_destination_signals(
        city(),
        TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
    )

    assert signals.attraction_count == 2


def test_destination_signals_read_stored_attractions(monkeypatch):
    SIGNAL_CACHE._values.clear()
    attractions = [
        AttractionSummary(name="Museum", category="museum", source="OpenStreetMap"),
        AttractionSummary(name="Viewpoint", category="viewpoint", source="OpenStreetMap"),
    ]

    monkeypatch.setattr(
        "solo_api.recommendation_signals.get_climate_normal",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=21,
            precipitation_mm=1,
            sunshine_hours=6,
            summary="Stored climate.",
        ),
    )
    monkeypatch.setattr(
        "solo_api.recommendation_signals.resolve_city_attractions",
        lambda **kwargs: attractions,
    )
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: AirQualitySummary(
            summary="Good air quality.",
            source="Open-Meteo",
            status="available",
        ),
    )

    signals = get_destination_signals(
        city(),
        TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
    )

    assert signals.attraction_count == 2


def test_destination_signals_fall_back_with_warning(monkeypatch):
    SIGNAL_CACHE._values.clear()

    def broken_climate(**kwargs):
        raise RuntimeError("weather down")

    monkeypatch.setattr("solo_api.recommendation_signals.get_climate_normal", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_month_climate_summary", broken_climate)
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr("solo_api.recommendation_signals.resolve_city_attractions", lambda **kwargs: [])
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_summary", lambda city: None)
    monkeypatch.setattr("solo_api.recommendation_signals.fetch_wikimedia_image", lambda city: None)
    monkeypatch.setattr(
        "solo_api.recommendation_signals.fetch_air_quality_summary",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("open-meteo down")),
    )

    destination = city()
    signals = get_destination_signals(
        destination,
        TravelWindow(id="may", start_date=date(2026, 5, 23), end_date=date(2026, 5, 25)),
    )

    assert signals.climate.average_temperature_c is None
    assert signals.attraction_count == 0
    assert signals.air_quality.status == "unavailable"
    assert any("Open-Meteo unavailable" in warning for warning in signals.warnings)
    assert any("Wikimedia unavailable" in warning for warning in signals.warnings)
    assert any("Open-Meteo air quality unavailable" in warning for warning in signals.warnings)


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
            "attraction_count": 4,
            "summary": f"{destination.city} summary.",
            "image_url": "https://images.example/city.jpg",
            "air_quality": AirQualitySummary(
                pm25=11.0,
                pm10=20.0,
                no2=None,
                summary="Fair air quality.",
                source="Open-Meteo",
                status="available",
            ),
            "warnings": [],
        }

    monkeypatch.setattr("solo_api.recommendations.get_destination_signals", fake_signals)
    stub_city_candidates(monkeypatch)
    body = recommended_destinations_search(
        month=5,
        region="PT",
        query="lis",
        radius_km=1200,
        min_population=300000,
    )

    assert body[0].id == "lisbon-pt"
    assert body[0].name == "Lisbon"
    assert body[0].coordinates.model_dump() == {"lat": 38.7223, "lng": -9.1393}
    assert body[0].travel_score == (
        body[0].score_breakdown.climate_score
        + body[0].score_breakdown.attraction_score
        + body[0].score_breakdown.popularity_score
    )
    assert body[0].top_attractions == []
    assert body[0].attraction_count == 4
    assert body[0].image_url == "https://images.example/city.jpg"
    assert body[0].air_quality is not None
    assert body[0].air_quality.status == "available"


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
