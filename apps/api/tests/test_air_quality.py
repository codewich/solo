import httpx

from solo_api.air_quality import fetch_air_quality_summary


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_fetch_air_quality_summary_uses_nearest_openaq_location(monkeypatch):
    calls: list[tuple[str, dict | None]] = []

    def fake_get(url: str, params: dict | None = None, headers: dict | None = None, timeout=None):
        calls.append((url, params))
        if url == "https://api.openaq.org/v3/locations":
            return FakeResponse({"results": [{"id": 2178, "name": "City monitor"}]})
        elif url == "https://api.openaq.org/v3/locations/2178/sensors":
            return FakeResponse({
                "results": [
                    {"id": 1, "parameter": {"name": "pm25"}},
                    {"id": 2, "parameter": {"name": "pm10"}},
                    {"id": 3, "parameter": {"name": "no2"}},
                ]
            })
        elif url == "https://api.openaq.org/v3/locations/2178/latest":
            return FakeResponse({
                "results": [
                    {"value": 8.5, "sensorsId": 1},
                    {"value": 18.0, "sensorsId": 2},
                    {"value": 31.0, "sensorsId": 3},
                ]
            })
        return FakeResponse({"results": []})

    monkeypatch.setattr("solo_api.air_quality.httpx.get", fake_get)

    summary = fetch_air_quality_summary(latitude=51.5072, longitude=-0.1276)

    assert calls[0] == (
        "https://api.openaq.org/v3/locations",
        {
            "coordinates": "51.5072,-0.1276",
            "radius": 25000,
            "limit": 1,
        },
    )
    assert calls[1][0] == "https://api.openaq.org/v3/locations/2178/sensors"
    assert calls[2][0] == "https://api.openaq.org/v3/locations/2178/latest"
    assert summary.pm25 == 8.5
    assert summary.pm10 == 18.0
    assert summary.no2 == 31.0
    assert summary.status == "available"
    assert "PM2.5 8.5" in summary.summary


def test_fetch_air_quality_summary_returns_unavailable_without_nearby_station(monkeypatch):
    monkeypatch.setattr(
        "solo_api.air_quality.httpx.get",
        lambda *args, **kwargs: FakeResponse({"results": []}),
    )

    summary = fetch_air_quality_summary(latitude=38.7223, longitude=-9.1393)

    assert summary.status == "unavailable"
    assert summary.pm25 is None


def test_fetch_air_quality_summary_raises_http_errors(monkeypatch):
    def broken_get(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("solo_api.air_quality.httpx.get", broken_get)

    try:
        fetch_air_quality_summary(latitude=51.5072, longitude=-0.1276)
    except httpx.HTTPError as error:
        assert "timed out" in str(error)
    else:
        raise AssertionError("Expected OpenAQ HTTP errors to be visible to caller fallback logic")
