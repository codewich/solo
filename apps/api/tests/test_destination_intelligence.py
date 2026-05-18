import os
from datetime import date

import httpx
import pytest

from solo_api.attractions import AttractionLookupError, count_attractions, fetch_attractions
from solo_api.attraction_service import resolve_city_attractions
from solo_api.cache import TtlCache
from solo_api.destination_intelligence import DestinationIntelligenceStepError, build_destination_intelligence
from solo_api.models import (
    AttractionSummary,
    ClimateSummary,
    DestinationIntelligenceRequest,
)
from solo_api.weather import fetch_climate_summary
from solo_api.weather import historical_archive_window

LIVE_ATTRACTION_CITIES = [
    ("Shanghai", "China", 31.2304, 121.4737),
    ("Beijing", "China", 39.9042, 116.4074),
    ("Chengdu", "China", 30.5728, 104.0668),
    ("Lisbon", "Portugal", 38.7223, -9.1393),
    ("Mexico City", "Mexico", 19.4326, -99.1332),
]


live_provider_required = pytest.mark.skipif(
    os.environ.get("SOLO_RUN_LIVE_PROVIDER_TESTS") != "1",
    reason="Set SOLO_RUN_LIVE_PROVIDER_TESTS=1 to query live attraction providers.",
)


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

    def fake_get(url: str, headers: dict, timeout, params: dict | None = None):
        if url == "https://en.wikipedia.org/w/api.php":
            return FakeResponse({"query": {"geosearch": []}})
        if url == "https://query.wikidata.org/sparql":
            return FakeResponse({"results": {"bindings": []}})
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
        captured.setdefault("query", data["data"])
        captured.setdefault("timeout", timeout)
        return FakeResponse({"elements": []})

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", lambda *args, **kwargs: FakeResponse({}))

    fetch_attractions(latitude=51.5072, longitude=-0.1276, city="London")

    query = str(captured["query"])
    assert '["tourism"~"museum|attraction|viewpoint|gallery' in query
    assert '["historic"~"castle|monument|archaeological_site' in query
    assert '["amenity"="place_of_worship"]' not in query
    assert '["historic"];' not in query
    assert captured["timeout"].read == 12.0


def test_fetch_attractions_falls_back_to_broader_osm_query(monkeypatch):
    queries: list[str] = []

    def fake_post(url: str, data: dict, headers: dict, timeout):
        queries.append(data["data"])
        if len(queries) == 1:
            return FakeResponse({"elements": []})
        return FakeResponse(
            {
                "elements": [
                    {
                        "id": 1,
                        "lat": 39.9163,
                        "lon": 116.3972,
                        "tags": {"name:en": "Temple of Heaven", "amenity": "place_of_worship"},
                    },
                    {
                        "id": 2,
                        "center": {"lat": 39.9259, "lon": 116.3967},
                        "tags": {"name": "景山公园", "leisure": "park"},
                    },
                ]
            }
        )

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", lambda *args, **kwargs: FakeResponse({}))

    attractions = fetch_attractions(latitude=39.9042, longitude=116.4074, city="Beijing")

    assert len(queries) == 2
    assert '["amenity"~"arts_centre|theatre|place_of_worship"]["name"]' in queries[1]
    assert 'relation(around:15000' in queries[1]
    assert [item.name for item in attractions[:2]] == ["Temple of Heaven", "景山公园"]
    assert attractions[0].category == "place_of_worship"


def test_fetch_attractions_falls_back_to_wikimedia_geosearch(monkeypatch):
    def fake_post(url: str, data: dict, headers: dict, timeout):
        return FakeResponse({"elements": []})

    def fake_get(url: str, **kwargs):
        if url == "https://en.wikipedia.org/w/api.php":
            assert kwargs["params"]["gscoord"] == "31.2304|121.4737"
            return FakeResponse(
                {
                    "query": {
                        "geosearch": [
                            {
                                "title": "Shanghai Museum",
                                "lat": 31.2303,
                                "lon": 121.4708,
                            },
                            {
                                "title": "Yu Garden",
                                "lat": 31.2272,
                                "lon": 121.4921,
                            },
                        ]
                    }
                }
            )
        if url == "https://en.wikipedia.org/api/rest_v1/page/summary/Shanghai":
            return FakeResponse({})
        if url == "https://query.wikidata.org/sparql":
            return FakeResponse({"results": {"bindings": []}})
        assert "Shanghai_Museum" in url or "Yu_Garden" in url
        return FakeResponse({"extract": "A notable Shanghai attraction."})

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=31.2304, longitude=121.4737, city="Shanghai")

    assert [item.name for item in attractions] == ["Shanghai Museum", "Yu Garden"]
    assert all(item.source == "Wikimedia" for item in attractions)
    assert attractions[0].description == "A notable Shanghai attraction."


def test_fetch_attractions_falls_back_to_wikidata_nearby_items(monkeypatch):
    def fake_post(url: str, data: dict, headers: dict, timeout):
        return FakeResponse({"elements": []})

    def fake_get(url: str, **kwargs):
        if url == "https://en.wikipedia.org/api/rest_v1/page/summary/Chengdu":
            return FakeResponse({})
        if url == "https://en.wikipedia.org/w/api.php":
            return FakeResponse({"query": {"geosearch": []}})
        assert url == "https://query.wikidata.org/sparql"
        assert "Point(104.0668 30.5728)" in kwargs["params"]["query"]
        return FakeResponse(
            {
                "results": {
                    "bindings": [
                        {
                            "itemLabel": {"value": "Wuhou Shrine"},
                            "location": {"value": "Point(104.047 30.647)"},
                            "typeLabel": {"value": "tourist attraction"},
                        },
                        {
                            "itemLabel": {"value": "Jinli"},
                            "location": {"value": "Point(104.048 30.645)"},
                            "typeLabel": {"value": "street"},
                        },
                    ]
                }
            }
        )

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=30.5728, longitude=104.0668, city="Chengdu")

    assert [item.name for item in attractions] == ["Wuhou Shrine", "Jinli"]
    assert attractions[0].source == "Wikidata"
    assert attractions[0].latitude == 30.647
    assert attractions[0].longitude == 104.047


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
    assert '["tourism"~"museum|attraction|viewpoint|gallery' in str(calls[1]["query"])


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

    def fake_get(url: str, headers: dict, timeout, params: dict | None = None):
        if url == "https://en.wikipedia.org/w/api.php":
            return FakeResponse({"query": {"geosearch": []}})
        assert headers["User-Agent"].startswith("solo-travel-planner")
        return FakeHttpErrorResponse(403)

    monkeypatch.setattr("solo_api.attractions.httpx.post", fake_post)
    monkeypatch.setattr("solo_api.attractions.httpx.get", fake_get)

    attractions = fetch_attractions(latitude=41.1579, longitude=-8.6291, city="Porto")

    assert len(attractions) == 1
    assert attractions[0].name == "Clerigos Tower"
    assert attractions[0].description is None


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
        "solo_api.destination_intelligence.resolve_city_attractions",
        lambda **kwargs: [
            AttractionSummary(name="Belem Tower", category="attraction", source="OpenStreetMap")
        ],
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

    monkeypatch.setattr("solo_api.destination_intelligence.resolve_city_attractions", broken_attractions)
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
    assert len(calls) == 3
    assert '["historic"~"castle|monument|archaeological_site"]["name"]' in calls[0]
    assert "historic" not in calls[1]
    assert '["amenity"~"arts_centre|theatre|place_of_worship"]["name"]' in calls[2]


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
    def flaky_attractions(**kwargs):
        calls["attractions"] += 1
        if calls["attractions"] == 1:
            raise AttractionLookupError(
                service="OpenStreetMap",
                message="OpenStreetMap timed out while querying nearby attractions.",
                original_error=httpx.ReadTimeout("The read operation timed out"),
            )
        return [AttractionSummary(name="Museum of London", category="museum", source="OpenStreetMap")]

    monkeypatch.setattr("solo_api.destination_intelligence.resolve_city_attractions", flaky_attractions)

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
    monkeypatch.setattr("solo_api.destination_intelligence.resolve_city_attractions", lambda **kwargs: [])

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


def test_destination_intelligence_does_not_write_search_scoped_shared_cache(monkeypatch):
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
    monkeypatch.setattr("solo_api.destination_intelligence.resolve_city_attractions", lambda **kwargs: [])

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

    assert writes == []


def test_resolve_city_attractions_fetches_live_when_provider_cache_disabled(monkeypatch):
    calls = {"fetch": 0}
    fetched = [AttractionSummary(name="Shanghai Museum", category="museum", source="Wikidata")]

    monkeypatch.setenv("SOLO_DISABLE_PROVIDER_CACHE", "1")
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr(
        "solo_api.attraction_service.get_cached_attractions",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("cache should be disabled")),
    )
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.attraction_service.set_cached_attractions", lambda **kwargs: None)

    def fake_fetch(**kwargs):
        calls["fetch"] += 1
        return fetched

    monkeypatch.setattr("solo_api.attraction_service.fetch_attractions", fake_fetch)

    result = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
        use_cache=False,
    )

    assert result == fetched
    assert calls["fetch"] == 1


def test_resolve_city_attractions_env_cache_bypass_skips_stored_rows(monkeypatch):
    calls = {"fetch": 0}
    stored = [AttractionSummary(name="Old cached place", category="museum", source="OpenStreetMap")]
    fresh = [AttractionSummary(name="Fresh live place", category="museum", source="Wikidata")]

    monkeypatch.setenv("SOLO_DISABLE_PROVIDER_CACHE", "1")
    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: stored)
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)
    monkeypatch.setattr("solo_api.attraction_service.set_cached_attractions", lambda **kwargs: None)

    def fake_fetch(**kwargs):
        calls["fetch"] += 1
        return fresh

    monkeypatch.setattr("solo_api.attraction_service.fetch_attractions", fake_fetch)

    result = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
    )

    assert result == fresh
    assert calls["fetch"] == 1


def test_resolve_city_attractions_writes_and_reads_city_provider_cache(monkeypatch):
    fetched = [AttractionSummary(name="Yu Garden", category="garden", source="Wikidata")]
    cached_payload: list[AttractionSummary] | None = None
    calls = {"fetch": 0}

    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr(
        "solo_api.attraction_service.get_cached_attractions",
        lambda **kwargs: cached_payload,
    )
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)

    def fake_set_cache(**kwargs):
        nonlocal cached_payload
        cached_payload = kwargs["attractions"]

    def fake_fetch(**kwargs):
        calls["fetch"] += 1
        return fetched

    monkeypatch.setattr("solo_api.attraction_service.set_cached_attractions", fake_set_cache)
    monkeypatch.setattr("solo_api.attraction_service.fetch_attractions", fake_fetch)

    first = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
    )
    second = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
    )

    assert first == fetched
    assert second == fetched
    assert calls["fetch"] == 1


@live_provider_required
@pytest.mark.parametrize("city,country,latitude,longitude", LIVE_ATTRACTION_CITIES)
def test_live_attraction_providers_return_city_results(city, country, latitude, longitude, monkeypatch):
    monkeypatch.setenv("SOLO_DISABLE_PROVIDER_CACHE", "1")

    try:
        attractions = resolve_city_attractions(
            city_id=None,
            city=city,
            country=country,
            latitude=latitude,
            longitude=longitude,
            use_cache=False,
        )
    except AttractionLookupError as error:
        if isinstance(error.original_error, httpx.ConnectError):
            pytest.skip(f"Live provider network unavailable: {error.original_error}")
        raise

    assert attractions, f"{city}, {country} returned no attractions from live providers"
    assert all(attraction.name for attraction in attractions)
    assert all(attraction.source in {"OpenStreetMap", "Wikimedia", "Wikidata"} for attraction in attractions)


@live_provider_required
def test_city_attraction_cache_matches_live_provider_result(monkeypatch):
    try:
        live = resolve_city_attractions(
            city_id=None,
            city="Shanghai",
            country="China",
            latitude=31.2304,
            longitude=121.4737,
            use_cache=False,
        )
    except AttractionLookupError as error:
        if isinstance(error.original_error, httpx.ConnectError):
            pytest.skip(f"Live provider network unavailable: {error.original_error}")
        raise
    cached_payload: list[AttractionSummary] | None = None

    monkeypatch.setattr("solo_api.attraction_service.get_stored_attractions", lambda city_id: [])
    monkeypatch.setattr(
        "solo_api.attraction_service.get_cached_attractions",
        lambda **kwargs: cached_payload,
    )
    monkeypatch.setattr("solo_api.attraction_service.store_attractions", lambda **kwargs: None)

    def fake_set_cache(**kwargs):
        nonlocal cached_payload
        cached_payload = kwargs["attractions"]

    monkeypatch.setattr("solo_api.attraction_service.set_cached_attractions", fake_set_cache)
    monkeypatch.setattr("solo_api.attraction_service.fetch_attractions", lambda **kwargs: live)

    first = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
    )
    second = resolve_city_attractions(
        city_id="1796236",
        city="Shanghai",
        country="China",
        latitude=31.2304,
        longitude=121.4737,
    )

    assert first == live
    assert second == live
