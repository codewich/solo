from datetime import date

import httpx

from solo_api.attractions import AttractionLookupError, count_attractions, fetch_attractions
from solo_api.cache import TtlCache
from solo_api.cost_of_living import unavailable_cost_of_living_summary
from solo_api.destination_intelligence import DestinationIntelligenceStepError, build_destination_intelligence
from solo_api.hotels import summarize_hotel_prices
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
                    "temperature_2m_min": [16.0, 18.0],
                    "temperature_2m_max": [27.0, 29.0],
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
    assert summary.average_temperature_min_c == 17.0
    assert summary.average_temperature_max_c == 28.0
    assert summary.precipitation_mm == 4.0
    assert summary.sunshine_hours == 3.0
    assert calls[0][0] == "https://archive-api.open-meteo.com/v1/archive"
    assert "temperature_2m_min" in calls[0][1]["daily"]
    assert "temperature_2m_max" in calls[0][1]["daily"]


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


def test_fetch_attractions_uses_narrow_named_poi_query(monkeypatch):
    captured: dict[str, object] = {}

    def fake_post(url: str, data: dict, headers: dict, timeout):
        captured["query"] = data["data"]
        captured["timeout"] = timeout
        return FakeResponse({"elements": []})

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", lambda *args, **kwargs: FakeResponse({}))

    fetch_attractions(latitude=51.5072, longitude=-0.1276, city="London")

    query = str(captured["query"])
    assert '["tourism"~"museum|attraction|viewpoint|gallery"]["name"]' in query
    assert '["historic"~"castle|monument|archaeological_site"]["name"]' in query
    assert '["amenity"="place_of_worship"]' not in query
    assert '["historic"];' not in query
    assert captured["timeout"].read == 12.0


def test_count_attractions_uses_overpass_wrapper(monkeypatch):
    calls: list[dict[str, object]] = []

    class FakeOverpassApi:
        def __init__(self, *, user_agent: str, timeout: int):
            calls.append({"user_agent": user_agent, "timeout": timeout})

        def get(self, query: str, *, responseformat: str, build: bool):
            calls.append({"query": query, "responseformat": responseformat, "build": build})
            return {"elements": [{"id": 1}, {"id": 2}, {"id": 3}]}

    monkeypatch.setattr("solo_api.attractions.overpass.API", FakeOverpassApi)

    count = count_attractions(latitude=51.5072, longitude=-0.1276, radius_m=2500)

    assert count == 3
    assert calls[0] == {"user_agent": "solo-travel-planner/0.1", "timeout": 12}
    assert calls[1]["responseformat"] == "json"
    assert calls[1]["build"] is False
    assert '["tourism"~"museum|attraction|viewpoint|gallery"]["name"]' in str(calls[1]["query"])


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


def test_hotel_summary_returns_unavailable_without_provider():
    summary = summarize_hotel_prices(
        city_code="LIS",
        check_in_date=date(2026, 5, 22),
        check_out_date=date(2026, 5, 25),
    )

    assert summary.status == "unavailable"
    assert summary.sample_size == 0


def test_cost_of_living_returns_unavailable_summary():
    summary = unavailable_cost_of_living_summary(city="Lisbon")

    assert summary.status == "unavailable"
    assert "Lisbon" in summary.summary


def test_destination_intelligence_endpoint_aggregates_sources(monkeypatch):
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_month_climate_summary",
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

    result = build_destination_intelligence(
        DestinationIntelligenceRequest(
            destination_city="Lisbon",
            country="Portugal",
            latitude=38.7223,
            longitude=-9.1393,
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 25),
        )
    )

    assert result.destination_city == "Lisbon"
    assert result.climate.average_temperature_c == 23.0
    assert result.attractions[0].name == "Belem Tower"
    assert result.hotels.median_nightly_price == 118.0
    assert result.cost_of_living.status == "unavailable"


def test_destination_intelligence_endpoint_reports_failing_service(monkeypatch):
    from solo_api.destination_intelligence import INTELLIGENCE_CACHE

    INTELLIGENCE_CACHE._values.clear()

    def broken_climate(**kwargs):
        raise httpx.TimeoutException("timed out while contacting Open-Meteo")

    monkeypatch.setattr("solo_api.destination_intelligence.fetch_month_climate_summary", broken_climate)
    try:
        build_destination_intelligence(
            DestinationIntelligenceRequest(
                destination_city="Lisbon",
                country="Portugal",
                latitude=38.7223,
                longitude=-9.1393,
                start_date=date(2026, 5, 22),
                end_date=date(2026, 5, 25),
            )
        )
    except DestinationIntelligenceStepError as error:
        assert error.step == "climate"
        assert error.service == "Open-Meteo"
        assert error.message == (
            "Open-Meteo failed during climate lookup: timed out while contacting Open-Meteo"
        )
    else:
        raise AssertionError("Expected climate lookup failure")


def test_destination_intelligence_keeps_partial_result_when_attractions_timeout(monkeypatch):
    from solo_api.destination_intelligence import INTELLIGENCE_CACHE

    INTELLIGENCE_CACHE._values.clear()

    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_month_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=20.0,
            precipitation_mm=3.0,
            sunshine_hours=7.0,
            summary="Mild weather.",
        ),
    )

    def broken_attractions(**kwargs):
        raise AttractionLookupError(
            service="OpenStreetMap",
            message="OpenStreetMap timed out while querying nearby attractions.",
            original_error=httpx.ReadTimeout("The read operation timed out"),
        )

    monkeypatch.setattr("solo_api.destination_intelligence.fetch_attractions", broken_attractions)
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

    result = build_destination_intelligence(
        DestinationIntelligenceRequest(
            destination_city="Metropolitan City of Milan",
            country="Italy",
            latitude=45.4642,
            longitude=9.19,
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 25),
        )
    )

    assert result.climate.average_temperature_c == 20.0
    assert result.attractions == []
    assert [warning.model_dump() for warning in result.warnings] == [
        {
            "step": "attractions",
            "service": "OpenStreetMap",
            "message": (
                "OpenStreetMap failed during attractions lookup: "
                "OpenStreetMap timed out while querying nearby attractions."
            ),
        }
    ]


def test_fetch_attractions_reports_openstreetmap_timeout_specifically(monkeypatch):
    def broken_post(url: str, data: dict, headers: dict, timeout):
        raise httpx.ReadTimeout("The read operation timed out")

    monkeypatch.setattr("solo_api.attractions.httpx.post", broken_post)

    try:
        fetch_attractions(latitude=40.8518, longitude=14.2681, city="Metropolitan City of Naples")
    except AttractionLookupError as error:
        assert error.service == "OpenStreetMap"
        assert str(error) == "OpenStreetMap timed out while querying nearby attractions."
    else:
        raise AssertionError("Expected an OpenStreetMap-specific attraction lookup error")


def test_fetch_attractions_retries_with_lighter_query_after_timeout(monkeypatch):
    calls: list[str] = []

    def fake_post(url: str, data: dict, headers: dict, timeout):
        calls.append(data["data"])
        if len(calls) == 1:
            raise httpx.ReadTimeout("The read operation timed out")
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": 1,
                        "lat": 51.5138,
                        "lon": -0.0995,
                        "tags": {"name": "Museum of London", "tourism": "museum"},
                    }
                ]
            }
        )

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", lambda *args, **kwargs: FakeResponse({}))

    attractions = fetch_attractions(latitude=51.5072, longitude=-0.1276, city="London")

    assert [item.name for item in attractions] == ["Museum of London"]
    assert len(calls) == 2
    assert '["historic"~"castle|monument|archaeological_site"]["name"]' in calls[0]
    assert "historic" not in calls[1]


def test_destination_intelligence_does_not_cache_partial_warning_results(monkeypatch):
    from solo_api.destination_intelligence import INTELLIGENCE_CACHE

    INTELLIGENCE_CACHE._values.clear()
    calls = {"attractions": 0}

    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_month_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=18.0,
            precipitation_mm=4.0,
            sunshine_hours=6.0,
            summary="Mild weather.",
        ),
    )
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

    def flaky_attractions(**kwargs):
        calls["attractions"] += 1
        if calls["attractions"] == 1:
            raise AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap timed out while querying nearby attractions.",
                original_error=httpx.ReadTimeout("The read operation timed out"),
            )
        return [AttractionSummary(name="Museum of London", category="museum", source="OpenStreetMap")]

    monkeypatch.setattr("solo_api.destination_intelligence.fetch_attractions", flaky_attractions)

    request = DestinationIntelligenceRequest(
        destination_city="London",
        country="United Kingdom",
        latitude=51.5072,
        longitude=-0.1276,
        start_date=date(2026, 5, 22),
        end_date=date(2026, 5, 25),
    )
    first = build_destination_intelligence(request)
    second = build_destination_intelligence(request)

    assert first.warnings
    assert second.warnings == []
    assert second.attractions[0].name == "Museum of London"
    assert calls["attractions"] == 2


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

    monkeypatch.setattr("solo_api.destination_intelligence.fetch_month_climate_summary", fake_climate)
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


def test_destination_intelligence_writes_to_shared_cache(monkeypatch):
    from solo_api.destination_intelligence import INTELLIGENCE_CACHE, build_destination_intelligence

    INTELLIGENCE_CACHE._values.clear()
    writes = []

    monkeypatch.setattr(
        "solo_api.destination_intelligence.get_api_cache",
        lambda key: None,
        raising=False,
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.set_api_cache",
        lambda key, payload, ttl_seconds, provider: writes.append(
            (key, payload, ttl_seconds, provider)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        "solo_api.destination_intelligence.fetch_month_climate_summary",
        lambda **kwargs: ClimateSummary(
            average_temperature_c=19.0,
            precipitation_mm=1.0,
            sunshine_hours=4.0,
            summary="Cached weather.",
        ),
    )
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

    build_destination_intelligence(
        DestinationIntelligenceRequest(
            destination_city="Cacheville",
            country="Portugal",
            latitude=38.0,
            longitude=-9.0,
            start_date=date(2026, 5, 22),
            end_date=date(2026, 5, 25),
        )
    )

    assert writes
    assert writes[0][0].startswith("destination_intelligence:")
    assert writes[0][3] == "destination_intelligence"
