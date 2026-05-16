from datetime import date

import httpx
from fastapi.testclient import TestClient

from solo_api.attractions import fetch_attractions
from solo_api.cache import TtlCache
from solo_api.cost_of_living import StaticCostOfLivingProvider
from solo_api.hotels import summarize_hotel_prices
from solo_api.main import app
from solo_api.models import (
    AttractionSummary,
    ClimateSummary,
    DestinationIntelligenceRequest,
    HotelPriceSummary,
)
from solo_api.weather import fetch_climate_summary
from solo_api.weather import historical_archive_window


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeHttpErrorResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://en.wikipedia.org/api/rest_v1/page/summary/Porto")

    def raise_for_status(self) -> None:
        raise httpx.HTTPStatusError(
            f"Client error '{self.status_code}'",
            request=self.request,
            response=httpx.Response(self.status_code, request=self.request),
        )

    def json(self) -> dict:
        return {}


def test_ttl_cache_returns_value_before_expiry(monkeypatch):
    now = 1000.0
    monkeypatch.setattr("solo_api.cache.time.monotonic", lambda: now)
    cache = TtlCache(ttl_seconds=60)

    cache.set("lisbon", {"score": 1})

    assert cache.get("lisbon") == {"score": 1}


def test_ttl_cache_expires_value(monkeypatch):
    current = {"now": 1000.0}
    monkeypatch.setattr("solo_api.cache.time.monotonic", lambda: current["now"])
    cache = TtlCache(ttl_seconds=60)
    cache.set("lisbon", {"score": 1})

    current["now"] = 1061.0

    assert cache.get("lisbon") is None


def test_destination_intelligence_request_accepts_coordinates_and_dates():
    request = DestinationIntelligenceRequest(
        destination_city="Lisbon",
        country="Portugal",
        latitude=38.7223,
        longitude=-9.1393,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
    )

    assert request.destination_city == "Lisbon"


def test_fetch_climate_summary_uses_open_meteo(monkeypatch):
    calls = []

    def fake_get(url: str, params: dict, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(
            {
                "daily": {
                    "temperature_2m_mean": [22.0, 24.0],
                    "precipitation_sum": [1.0, 3.0],
                    "sunshine_duration": [3600.0, 7200.0],
                }
            }
        )

    monkeypatch.setattr("solo_api.weather.httpx.get", fake_get)

    summary = fetch_climate_summary(
        latitude=38.7223,
        longitude=-9.1393,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 23),
    )

    assert summary.average_temperature_c == 23.0
    assert summary.precipitation_mm == 4.0
    assert summary.sunshine_hours == 3.0
    assert calls[0][0] == "https://archive-api.open-meteo.com/v1/archive"


def test_historical_archive_window_shifts_future_dates_to_previous_year():
    start_date, end_date = historical_archive_window(
        start_date=date(2026, 8, 28),
        end_date=date(2026, 8, 31),
        latest_available=date(2026, 5, 16),
    )

    assert start_date == date(2025, 8, 28)
    assert end_date == date(2025, 8, 31)


def test_fetch_attractions_combines_overpass_and_wikimedia_results(monkeypatch):
    def fake_post(url: str, data: dict, headers: dict, timeout):
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": 1,
                        "lat": 38.7139,
                        "lon": -9.1394,
                        "tags": {"name": "Castelo de Sao Jorge", "historic": "castle"},
                    },
                    {
                        "id": 2,
                        "lat": 38.6979,
                        "lon": -9.2067,
                        "tags": {"name": "Belem Tower", "tourism": "attraction"},
                    },
                ]
            }
        )

    def fake_get(url: str, headers: dict, timeout):
        assert url == "https://en.wikipedia.org/api/rest_v1/page/summary/Lisbon"
        assert headers["User-Agent"].startswith("solo-travel-planner")
        return FakeResponse(
            {
                "extract": (
                    "Lisbon is Portugal's capital, known for hills, tiled streets, "
                    "and maritime history."
                )
            }
        )

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=38.7223, longitude=-9.1393, city="Lisbon")

    assert [item.name for item in attractions] == ["Castelo de Sao Jorge", "Belem Tower"]
    assert attractions[0].category == "castle"
    assert attractions[0].description == (
        "Lisbon is Portugal's capital, known for hills, tiled streets, and maritime history."
    )


def test_fetch_attractions_keeps_pois_when_wikimedia_summary_is_forbidden(monkeypatch):
    def fake_post(url: str, data: dict, headers: dict, timeout):
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": 1,
                        "lat": 41.1457,
                        "lon": -8.6146,
                        "tags": {"name": "Clerigos Tower", "tourism": "attraction"},
                    }
                ]
            }
        )

    def fake_get(url: str, headers: dict, timeout):
        assert headers["User-Agent"].startswith("solo-travel-planner")
        return FakeHttpErrorResponse(403)

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=41.1579, longitude=-8.6291, city="Porto")

    assert len(attractions) == 1
    assert attractions[0].name == "Clerigos Tower"
    assert attractions[0].description is None


def test_hotel_summary_returns_unavailable_without_credentials(monkeypatch):
    monkeypatch.delenv("AMADEUS_CLIENT_ID", raising=False)
    monkeypatch.delenv("AMADEUS_CLIENT_SECRET", raising=False)

    summary = summarize_hotel_prices(
        city_code="LIS",
        check_in_date=date(2026, 5, 22),
        check_out_date=date(2026, 5, 25),
    )

    assert summary.status == "unavailable"
    assert summary.sample_size == 0


def test_static_cost_of_living_provider_returns_city_summary():
    provider = StaticCostOfLivingProvider()

    summary = provider.summary_for(city="Lisbon", country="Portugal")

    assert summary.currency == "EUR"
    assert "Lisbon" in summary.summary


def test_destination_intelligence_endpoint_aggregates_sources(monkeypatch):
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=23.0,
            precipitation_mm=4.0,
            sunshine_hours=3.0,
            summary="Warm and bright.",
        ),
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_attractions",
        lambda **kwargs: [
            AttractionSummary(name="Belem Tower", category="attraction", source="OpenStreetMap")
        ],
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.summarize_hotel_prices",
        lambda **kwargs: HotelPriceSummary(
            average_nightly_price=121.5,
            median_nightly_price=118.0,
            currency="EUR",
            sample_size=12,
        ),
    )

    response = TestClient(app).post(
        "/destination-intelligence",
        json={
            "destination_city": "Lisbon",
            "country": "Portugal",
            "latitude": 38.7223,
            "longitude": -9.1393,
            "start_date": "2026-05-22",
            "end_date": "2026-05-25",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["destination_city"] == "Lisbon"
    assert payload["climate"]["average_temperature_c"] == 23.0
    assert payload["attractions"][0]["name"] == "Belem Tower"
    assert payload["hotels"]["median_nightly_price"] == 118.0
    assert payload["cost_of_living"]["currency"] == "EUR"


def test_destination_intelligence_uses_cache(monkeypatch):
    from solo_api.destination_intelligence import INTELLIGENCE_CACHE, build_destination_intelligence

    INTELLIGENCE_CACHE._values.clear()
    calls = {"climate": 0}

    def fake_climate(**kwargs):
        calls["climate"] += 1
        return ClimateSummary(
            average_temperature_c=19.0,
            precipitation_mm=1.0,
            sunshine_hours=4.0,
            summary="Cached weather.",
        )

    monkeypatch.setattr("solo_api.destination_intelligence.fetch_climate_summary", fake_climate)
    monkeypatch.setattr("solo_api.destination_intelligence.fetch_attractions", lambda **kwargs: [])
    monkeypatch.setattr(
        "solo_api.destination_intelligence.summarize_hotel_prices",
        lambda **kwargs: HotelPriceSummary(
            average_nightly_price=None,
            median_nightly_price=None,
            currency=None,
            sample_size=0,
            status="unavailable",
        ),
    )

    request = DestinationIntelligenceRequest(
        destination_city="Cacheville",
        country="Portugal",
        latitude=38.0,
        longitude=-9.0,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
    )

    first = build_destination_intelligence(request)
    second = build_destination_intelligence(request)

    assert first == second
    assert calls["climate"] == 1
