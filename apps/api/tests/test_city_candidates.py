from solo_api.city_candidates import CITY_CANDIDATE_CACHE, search_city_candidates


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_search_city_candidates_uses_geodb_filters(monkeypatch):
    CITY_CANDIDATE_CACHE._values.clear()
    monkeypatch.setenv("GEODB_RAPIDAPI_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    calls = []

    def fake_get(url: str, params: dict, headers: dict, timeout):
        calls.append((url, params, headers, timeout))
        return FakeResponse(
            {
                "data": [
                    {
                        "id": 2267057,
                        "wikiDataId": "Q597",
                        "type": "CITY",
                        "name": "Lisbon",
                        "country": "Portugal",
                        "countryCode": "PT",
                        "region": "Lisbon",
                        "latitude": 38.7223,
                        "longitude": -9.1393,
                        "population": 544851,
                        "timezone": "Europe/Lisbon",
                    }
                ]
            }
        )

    monkeypatch.setattr("solo_api.city_candidates.httpx.get", fake_get)

    cities = search_city_candidates(
        latitude=51.5072,
        longitude=-0.1276,
        radius_km=80,
        min_population=250000,
        limit=12,
        region="PT",
        query="Lis",
    )

    assert cities[0].id == "Q597"
    assert cities[0].city == "Lisbon"
    assert cities[0].population == 544851
    assert calls[0][1] == {
        "location": "+51.5072-0.1276",
        "radius": 80,
        "distanceUnit": "KM",
        "minPopulation": 250000,
        "limit": 10,
        "sort": "-population",
        "types": "CITY",
        "languageCode": "en",
        "namePrefix": "Lis",
        "countryIds": "PT",
    }
    assert calls[0][2]["X-RapidAPI-Host"] == "wft-geo-db.p.rapidapi.com"


def test_search_city_candidates_filters_large_radius_locally(monkeypatch):
    CITY_CANDIDATE_CACHE._values.clear()
    monkeypatch.setenv("GEODB_RAPIDAPI_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    calls = []

    def fake_get(url: str, params: dict, headers: dict, timeout):
        calls.append(params)
        return FakeResponse(
            {
                "data": [
                    {
                        "id": 2267057,
                        "name": "Lisbon",
                        "country": "Portugal",
                        "countryCode": "PT",
                        "latitude": 38.7223,
                        "longitude": -9.1393,
                        "population": 544851,
                    },
                    {
                        "id": 5128581,
                        "name": "New York City",
                        "country": "United States of America",
                        "countryCode": "US",
                        "latitude": 40.7128,
                        "longitude": -74.006,
                        "population": 8804190,
                    },
                ]
            }
        )

    monkeypatch.setattr("solo_api.city_candidates.httpx.get", fake_get)

    cities = search_city_candidates(
        latitude=51.5072,
        longitude=-0.1276,
        radius_km=2000,
        min_population=250000,
        limit=12,
        query="Lis",
    )

    assert [city.city for city in cities] == ["Lisbon"]
    assert "location" not in calls[0]
    assert calls[0]["countryIds"]


def test_search_city_candidates_uses_cache(monkeypatch):
    CITY_CANDIDATE_CACHE._values.clear()
    monkeypatch.setenv("GEODB_RAPIDAPI_KEY", "test-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    calls = {"count": 0}

    def fake_get(url: str, params: dict, headers: dict, timeout):
        calls["count"] += 1
        return FakeResponse(
            {
                "data": [
                    {
                        "id": 1,
                        "name": "Porto",
                        "country": "Portugal",
                        "countryCode": "PT",
                        "latitude": 41.1579,
                        "longitude": -8.6291,
                        "population": 231800,
                    }
                ]
            }
        )

    monkeypatch.setattr("solo_api.city_candidates.httpx.get", fake_get)

    kwargs = {
        "latitude": 51.5072,
        "longitude": -0.1276,
        "radius_km": 2000,
        "min_population": 200000,
        "limit": 10,
    }
    first = search_city_candidates(**kwargs)
    second = search_city_candidates(**kwargs)

    assert first == second
    assert calls["count"] == 1
