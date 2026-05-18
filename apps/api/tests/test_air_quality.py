from datetime import date

import httpx

from solo_api.air_quality import air_quality_sample_year, fetch_air_quality_summary


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_air_quality_sample_year_uses_current_year_minus_one():
    assert air_quality_sample_year(today=date(2026, 5, 18)) == 2025


def test_fetch_air_quality_summary_queries_open_meteo_month_and_averages(monkeypatch):
    calls: list[tuple[str, dict | None]] = []

    def fake_get(url: str, params: dict | None = None, timeout=None):
        calls.append((url, params))
        return FakeResponse(
            {
                "hourly": {
                    "european_aqi": [18, 22, None],
                    "us_aqi": [40, 60, None],
                    "pm2_5": [8.0, 10.0, None],
                    "pm10": [18.0, 22.0, None],
                    "nitrogen_dioxide": [20.0, 30.0, None],
                }
            }
        )

    monkeypatch.setattr("solo_api.air_quality.httpx.get", fake_get)

    summary = fetch_air_quality_summary(
        latitude=48.8566,
        longitude=2.3522,
        year=2025,
        month=5,
    )

    assert calls == [
        (
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            {
                "latitude": 48.8566,
                "longitude": 2.3522,
                "start_date": "2025-05-01",
                "end_date": "2025-05-31",
                "hourly": "european_aqi,us_aqi,pm2_5,pm10,nitrogen_dioxide",
                "timezone": "auto",
            },
        )
    ]
    assert summary.european_aqi == 20.0
    assert summary.us_aqi == 50.0
    assert summary.pm25 == 9.0
    assert summary.pm10 == 20.0
    assert summary.no2 == 25.0
    assert summary.source == "Open-Meteo"
    assert summary.status == "available"
    assert "European AQI 20.0" in summary.summary


def test_fetch_air_quality_summary_returns_unavailable_without_values(monkeypatch):
    monkeypatch.setattr(
        "solo_api.air_quality.httpx.get",
        lambda *args, **kwargs: FakeResponse({"hourly": {"european_aqi": [None], "us_aqi": [None]}}),
    )

    summary = fetch_air_quality_summary(latitude=38.7223, longitude=-9.1393, year=2025, month=5)

    assert summary.status == "unavailable"
    assert summary.european_aqi is None
    assert summary.us_aqi is None


def test_fetch_air_quality_summary_returns_unavailable_on_http_errors(monkeypatch):
    def broken_get(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("solo_api.air_quality.httpx.get", broken_get)

    summary = fetch_air_quality_summary(latitude=51.5072, longitude=-0.1276, year=2025, month=5)

    assert summary.status == "unavailable"
