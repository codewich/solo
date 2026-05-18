from fastapi.testclient import TestClient

from solo_api.main import app


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_city_geocoding_returns_normalized_suggestions(monkeypatch):
    calls = []

    def fake_get(url: str, params: dict, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(
            {
                "results": [
                    {
                        "id": 2643743,
                        "name": "London",
                        "country": "United Kingdom",
                        "country_code": "GB",
                        "admin1": "England",
                        "latitude": 51.5085,
                        "longitude": -0.1257,
                        "timezone": "Europe/London",
                    }
                ]
            }
        )

    monkeypatch.setattr("solo_api.geocoding.httpx.get", fake_get)

    response = TestClient(app).get("/geocode/cities", params={"query": "London"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "2643743",
            "name": "London",
            "country": "United Kingdom",
            "country_code": None,
            "admin1": "England",
            "latitude": 51.5085,
            "longitude": -0.1257,
            "timezone": "Europe/London",
        }
    ]
    assert calls[0][0] == "https://geocoding-api.open-meteo.com/v1/search"
    assert calls[0][1]["name"] == "London"


def test_city_geocoding_rejects_short_queries():
    response = TestClient(app).get("/geocode/cities", params={"query": "L"})

    assert response.status_code == 200
    assert response.json() == []
